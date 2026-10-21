import math

import numpy as np
import pytest

from trafego_lab.amostra import make_synthetic_traffic
from trafego_lab.backtest import run_backtest, seasonal_naive
from trafego_lab.metricas import coverage, mae, mape
from trafego_lab.modelo import ForecastResult, choose_backend


def test_mae_and_mape():
    assert mae([10, 20], [12, 18]) == 2
    assert mape([10, 20], [12, 18]) == pytest.approx(15.0)


def test_mape_ignores_zero_actuals_and_handles_all_zero():
    assert mape([0, 10], [5, 11]) == pytest.approx(10.0)
    assert math.isnan(mape([0, 0], [1, 1]))


def test_coverage():
    assert coverage([1, 5, 9], [0, 0, 0], [2, 6, 8]) == pytest.approx(2 / 3)


def test_seasonal_naive_repeats_last_cycle():
    out = seasonal_naive(np.array([1, 2, 3, 4, 5]), horizon=5, season=2)
    assert list(out) == [4, 5, 4, 5, 4]


def test_choose_backend_validation():
    assert choose_backend("torch") == "torch"
    with pytest.raises(ValueError):
        choose_backend("gpu")


def test_run_backtest_with_fake_predictor_is_perfect():
    series = make_synthetic_traffic(weeks=2).set_index("timestamp")["vehicle_count"].astype(float)
    horizon = 24

    def oracle(history, h):
        truth = series.to_numpy()[len(history):len(history) + h]
        q = np.stack([truth] * 9, axis=1)
        return ForecastResult(point=truth, quantiles=q)

    result = run_backtest(series, horizon, oracle)
    assert result.mae == 0
    assert result.coverage == 1
    assert len(result.actual) == horizon
    assert result.baseline_mae > 0


def test_run_backtest_rejects_bad_horizon():
    series = make_synthetic_traffic(weeks=1).set_index("timestamp")["vehicle_count"].astype(float)
    with pytest.raises(ValueError):
        run_backtest(series, len(series), lambda h, n: None)
