"""Reading and preparing call-volume time series from CSV files."""

from __future__ import annotations

import warnings
from typing import IO

import pandas as pd

_DATE_HINTS = ("date", "time", "data", "hora", "timestamp", "datetime")
_VALUE_HINTS = (
    "calls", "offered", "chamadas", "ligacoes", "ligações", "volume", "count", "contagem", "value"
)


def load_csv(source: str | IO) -> pd.DataFrame:
    """Read a CSV from a path or file-like object, guessing the separator."""
    return pd.read_csv(source, sep=None, engine="python")


def _is_datetime_like(column: pd.Series, min_valid: float = 0.9) -> bool:
    if pd.api.types.is_datetime64_any_dtype(column):
        return True
    if not (pd.api.types.is_object_dtype(column) or pd.api.types.is_string_dtype(column)):
        return False
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)  # text columns: "could not infer format"
        parsed = pd.to_datetime(column, errors="coerce")
    return bool(parsed.notna().mean() >= min_valid)


def detect_columns(df: pd.DataFrame) -> tuple[str | None, str | None]:
    """Guess which column holds the timestamps and which holds the values.

    Returns ``(date_col, value_col)``; either may be ``None`` if nothing fits.
    """
    date_candidates = [c for c in df.columns if _is_datetime_like(df[c])]
    date_col = next(
        (c for c in date_candidates if any(h in str(c).lower() for h in _DATE_HINTS)),
        date_candidates[0] if date_candidates else None,
    )

    numeric = [
        c
        for c in df.columns
        if c != date_col and pd.api.types.is_numeric_dtype(df[c]) and df[c].notna().any()
    ]
    value_col = next(
        (c for c in numeric if any(h in str(c).lower() for h in _VALUE_HINTS)),
        numeric[0] if numeric else None,
    )
    return date_col, value_col


def prepare_series(df: pd.DataFrame, date_col: str, value_col: str) -> pd.Series:
    """Build a clean series: datetime index, sorted, no duplicates, no missing values.

    Duplicated timestamps are averaged.
    """
    out = pd.DataFrame(
        {
            "ts": pd.to_datetime(df[date_col], errors="coerce"),
            "value": pd.to_numeric(df[value_col], errors="coerce"),
        }
    ).dropna()
    if out.empty:
        raise ValueError("Nenhum dado válido nas colunas escolhidas.")
    series = out.groupby("ts")["value"].mean().sort_index()
    series.name = value_col
    return series


def resample_series(
    series: pd.Series, freq: str, how: str = "sum", fill: str = "interpolate"
) -> pd.Series:
    """Aggregate to a regular frequency (e.g. ``"30min"``, ``"h"``, ``"D"``) and fill empty slots.

    ``how`` is ``"sum"`` (counts of calls) or ``"mean"`` (rates, durations).
    ``fill`` says what to do with intervals that have no record: ``"zero"`` for counts of calls
    (a closed contact center has zero calls) or ``"interpolate"`` for gaps in a measurement.
    """
    if how not in ("sum", "mean"):
        raise ValueError("how deve ser 'sum' ou 'mean'.")
    if fill not in ("zero", "interpolate"):
        raise ValueError("fill deve ser 'zero' ou 'interpolate'.")
    grouped = series.resample(freq)
    if how == "sum":
        # min_count=1 keeps empty buckets as NaN so that ``fill`` decides what they become
        regular = grouped.sum(min_count=1)
    else:
        regular = grouped.mean()
    if fill == "zero":
        return regular.fillna(0.0)
    return regular.interpolate(limit_direction="both")


_QUEUE_HINTS = ("fila", "queue", "skill", "habilidade", "equipe", "team", "produto", "product", "departamento", "department")


def detect_queue_column(df: pd.DataFrame, date_col: str | None = None, value_col: str | None = None) -> str | None:
    """Guess an optional queue/team column: text with 2 to 20 distinct values, preferring names like "fila".

    Returns ``None`` when the file has no such column (the normal, single-queue case).
    """
    candidates = [
        c for c in df.columns
        if c not in (date_col, value_col)
        and not pd.api.types.is_numeric_dtype(df[c])
        and not _is_datetime_like(df[c])
        and 2 <= df[c].nunique() <= 20
    ]
    return next((c for c in candidates if any(h in str(c).lower() for h in _QUEUE_HINTS)), candidates[0] if candidates else None)


def split_by_queue(
    df: pd.DataFrame, date_col: str, value_col: str, queue_col: str, freq: str, how: str = "sum", fill: str = "zero"
) -> dict[str, pd.Series]:
    """One regular series per queue, all covering the same period (missing intervals are filled like ``resample_series``).

    The keys are the queue names, as text, in order of appearance.
    """
    if queue_col not in df.columns:
        raise ValueError(f"A coluna de fila '{queue_col}' não existe no arquivo.")
    series = {}
    for name, group in df.groupby(df[queue_col].astype(str), sort=False):
        series[str(name)] = resample_series(prepare_series(group, date_col, value_col), freq, how, fill)
    if not series:
        raise ValueError("Nenhuma fila encontrada.")
    index = pd.date_range(min(s.index[0] for s in series.values()), max(s.index[-1] for s in series.values()), freq=freq)
    return {name: s.reindex(index).fillna(0.0) for name, s in series.items()}
