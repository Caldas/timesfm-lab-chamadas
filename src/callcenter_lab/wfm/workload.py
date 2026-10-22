"""Average handling time (AHT, "TMA") and the workload it creates, in Erlangs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


# --- AHT models: the same ``for_index`` interface for every way of giving the AHT -------------
@dataclass(frozen=True)
class ConstantAHT:
    """The same AHT (seconds) for every interval."""

    seconds: float

    def __post_init__(self) -> None:
        if self.seconds <= 0:
            raise ValueError("O TMA deve ser maior que zero.")

    def for_index(self, index: pd.DatetimeIndex) -> np.ndarray:
        return np.full(len(index), float(self.seconds))


@dataclass(frozen=True)
class ProfileAHT:
    """AHT by weekday (0=Monday) and hour of day, with a default for anything not in the table."""

    table: pd.DataFrame  # columns: weekday, hour, aht_seconds
    default_seconds: float

    def __post_init__(self) -> None:
        missing = {"weekday", "hour", "aht_seconds"} - set(self.table.columns)
        if missing:
            raise ValueError(f"A tabela de TMA precisa das colunas weekday, hour e aht_seconds (faltam {sorted(missing)}).")
        if (self.table["aht_seconds"] <= 0).any() or self.default_seconds <= 0:
            raise ValueError("O TMA deve ser maior que zero.")

    def for_index(self, index: pd.DatetimeIndex) -> np.ndarray:
        lookup = {(int(r.weekday), int(r.hour)): float(r.aht_seconds) for r in self.table.itertuples()}
        return np.array(
            [lookup.get((int(d), int(h)), float(self.default_seconds)) for d, h in zip(index.day_of_week, index.hour)]
        )


@dataclass(frozen=True)
class SeriesAHT:
    """AHT given for each interval (e.g. from a file). Intervals outside the series use the default."""

    series: pd.Series  # indexed by interval start, seconds
    default_seconds: float

    def __post_init__(self) -> None:
        if (self.series <= 0).any() or self.default_seconds <= 0:
            raise ValueError("O TMA deve ser maior que zero.")

    def for_index(self, index: pd.DatetimeIndex) -> np.ndarray:
        return self.series.reindex(index).fillna(self.default_seconds).to_numpy(dtype=float)


def load_aht_csv(path: str | Path, default_seconds: float):
    """Read an AHT file: columns ``timestamp, aht_seconds`` (per interval) or ``weekday, hour, aht_seconds`` (profile)."""
    df = pd.read_csv(path)
    if {"timestamp", "aht_seconds"} <= set(df.columns):
        series = pd.Series(df["aht_seconds"].to_numpy(dtype=float), index=pd.to_datetime(df["timestamp"]))
        return SeriesAHT(series[~series.index.duplicated()].sort_index(), default_seconds)
    if {"weekday", "hour", "aht_seconds"} <= set(df.columns):
        return ProfileAHT(df[["weekday", "hour", "aht_seconds"]], default_seconds)
    raise ValueError("O arquivo de TMA precisa das colunas (timestamp, aht_seconds) ou (weekday, hour, aht_seconds).")


# --- Synthetic AHT, for when the real one is not available ------------------------------------
def synthetic_aht(index: pd.DatetimeIndex, base_seconds: float = 300.0, noise: float = 0.05, seed: int = 42) -> pd.Series:
    """An example AHT: slightly longer calls late in the day, Mondays a bit longer, plus reproducible noise.

    Only an illustration to practise with. It is NOT the AHT of any real operation.
    """
    if base_seconds <= 0 or not 0 <= noise < 1:
        raise ValueError("base_seconds deve ser > 0 e noise entre 0 e 1 (exclusive).")
    rng = np.random.default_rng(seed)
    hour = (index.hour + index.minute / 60).to_numpy()
    shape = 1 + 0.10 * np.sin((hour - 6) / 24 * 2 * np.pi) + np.where(index.day_of_week == 0, 0.05, 0.0)
    values = base_seconds * shape * rng.normal(1.0, noise, size=len(index))
    return pd.Series(np.maximum(values, 1.0), index=index, name="aht_seconds")


# --- Workload ---------------------------------------------------------------------------------
def workload_erlangs(calls, aht_seconds, interval_minutes: int):
    """Workload in Erlangs: calls x AHT / interval length in seconds (arrays or numbers)."""
    if interval_minutes <= 0:
        raise ValueError("interval_minutes deve ser maior que zero.")
    calls = np.asarray(calls, dtype=float)
    if np.any(calls < 0):
        raise ValueError("O número de chamadas não pode ser negativo.")
    return calls * np.asarray(aht_seconds, dtype=float) / (interval_minutes * 60)


def forecast_aht(model, history: pd.Series, horizon: int) -> np.ndarray:
    """Forecast the AHT with the same TimesFM engine used for calls (optional). Returns seconds."""
    from ..model import forecast

    result = forecast(model, history.to_numpy(dtype=float), horizon)
    return np.maximum(result.point, 1.0)
