"""Hide the end of a series, forecast it, and compare with what really happened."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .metricas import coverage, mae, mape
from .modelo import ForecastResult

# (history, horizon) -> forecast
Predictor = Callable[[np.ndarray, int], ForecastResult]


@dataclass(frozen=True)
class BacktestResult:
    history: pd.Series
    actual: pd.Series
    point: pd.Series
    lower: pd.Series
    upper: pd.Series
    baseline: pd.Series
    mae: float
    mape: float
    coverage: float
    baseline_mae: float


def seasonal_naive(history: np.ndarray, horizon: int, season: int) -> np.ndarray:
    """Repeat the last full season (e.g. last 24 hours, or last 7 days)."""
    if season < 1 or len(history) < season:
        raise ValueError("Histórico menor que um ciclo sazonal.")
    cycle = np.asarray(history[-season:], dtype=float)
    reps = int(np.ceil(horizon / season))
    return np.tile(cycle, reps)[:horizon]


def run_backtest(
    series: pd.Series, horizon: int, predictor: Predictor, season: int = 24
) -> BacktestResult:
    """Forecast the last ``horizon`` points of ``series`` using only the earlier points."""
    if horizon < 1 or horizon >= len(series):
        raise ValueError("horizon deve ser >= 1 e menor que o tamanho da série.")
    history, actual = series.iloc[:-horizon], series.iloc[-horizon:]
    result = predictor(history.to_numpy(), horizon)
    baseline = seasonal_naive(history.to_numpy(), horizon, min(season, len(history)))

    def as_series(values) -> pd.Series:
        return pd.Series(np.asarray(values, dtype=float), index=actual.index)

    return BacktestResult(
        history=history,
        actual=actual,
        point=as_series(result.point),
        lower=as_series(result.lower),
        upper=as_series(result.upper),
        baseline=as_series(baseline),
        mae=mae(actual, result.point),
        mape=mape(actual, result.point),
        coverage=coverage(actual, result.lower, result.upper),
        baseline_mae=mae(actual, baseline),
    )
