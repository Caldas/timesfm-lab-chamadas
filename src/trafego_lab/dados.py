"""Reading and preparing traffic time series from CSV files."""

from __future__ import annotations

from typing import IO

import pandas as pd

_DATE_HINTS = ("date", "time", "data", "hora", "timestamp", "datetime")
_VALUE_HINTS = ("volume", "count", "traffic", "flow", "vehicles", "veiculos", "contagem", "value")


def load_csv(source: str | IO) -> pd.DataFrame:
    """Read a CSV from a path or file-like object, guessing the separator."""
    return pd.read_csv(source, sep=None, engine="python")


def _is_datetime_like(column: pd.Series, min_valid: float = 0.9) -> bool:
    if pd.api.types.is_datetime64_any_dtype(column):
        return True
    if not (pd.api.types.is_object_dtype(column) or pd.api.types.is_string_dtype(column)):
        return False
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


def resample_series(series: pd.Series, freq: str, how: str = "sum") -> pd.Series:
    """Aggregate to a regular frequency (e.g. ``"h"``, ``"D"``) and fill small gaps.

    ``how`` is ``"sum"`` (counts) or ``"mean"`` (rates, speeds). Gaps are filled by linear
    interpolation so the model sees a regular grid.
    """
    if how not in ("sum", "mean"):
        raise ValueError("how deve ser 'sum' ou 'mean'.")
    grouped = series.resample(freq)
    if how == "sum":
        # min_count=1 keeps empty buckets as NaN instead of turning them into 0
        regular = grouped.sum(min_count=1)
    else:
        regular = grouped.mean()
    return regular.interpolate(limit_direction="both")
