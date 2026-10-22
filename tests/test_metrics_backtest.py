import math

import numpy as np
import pytest

from callcenter_lab.backtest import run_backtest, seasonal_naive
from callcenter_lab.metrics import bias_pct, coverage, mae, mape, wape
from callcenter_lab.model import ForecastResult, choose_backend
from callcenter_lab.synthetic import make_synthetic_calls


def _calls(weeks):
    return make_synthetic_calls(weeks=weeks).set_index("timestamp")["calls_offered"].astype(float)


def test_mae_and_mape():
    assert mae([10, 20], [12, 18]) == 2
    assert mape([10, 20], [12, 18]) == pytest.approx(15.0)


def test_mape_ignores_zero_actuals_and_handles_all_zero():
    assert mape([0, 10], [5, 11]) == pytest.approx(10.0)
    assert math.isnan(mape([0, 0], [1, 1]))


def test_wape_is_not_distorted_by_zero_intervals():
    # one closed interval (0 calls) and one busy one: WAPE = |errors| / total calls
    assert wape([0, 100], [5, 90]) == pytest.approx(15.0)
    assert math.isnan(wape([0, 0], [1, 1]))


def test_bias_sign_tells_over_or_under_forecast():
    assert bias_pct([100, 100], [110, 110]) == pytest.approx(10.0)  # forecast too high
    assert bias_pct([100, 100], [80, 80]) == pytest.approx(-20.0)  # forecast too low
    assert math.isnan(bias_pct([0], [1]))


def test_coverage():
    assert coverage([1, 5, 9], [0, 0, 0], [2, 6, 8]) == pytest.approx(2 / 3)


def test_seasonal_naive_repeats_last_cycle():
    out = seasonal_naive(np.array([1, 2, 3, 4, 5]), horizon=5, season=2)
    assert list(out) == [4, 5, 4, 5, 4]


def test_choose_backend_validation():
    assert choose_backend("torch") == "torch"
    with pytest.raises(ValueError):
        choose_backend("gpu")


def test_synthetic_calls_follow_opening_hours():
    df = make_synthetic_calls(weeks=2)
    stamps = df["timestamp"]
    sunday = df[stamps.dt.dayofweek == 6]
    night = df[stamps.dt.hour < 8]
    assert (sunday["calls_offered"] == 0).all()
    assert (night["calls_offered"] == 0).all()
    assert df[stamps.dt.dayofweek == 0]["calls_offered"].max() > 0


def test_run_backtest_with_fake_predictor_is_perfect():
    series = _calls(3)
    horizon = 48

    def oracle(history, h):
        truth = series.to_numpy()[len(history):len(history) + h]
        return ForecastResult(point=truth, quantiles=np.stack([truth] * 9, axis=1))

    result = run_backtest(series, horizon, oracle)
    assert result.mae == 0
    assert result.wape == 0
    assert result.bias_pct == 0
    assert result.coverage == 1
    assert len(result.actual) == horizon
    assert result.baseline_wape > 0


def test_run_backtest_rejects_bad_horizon():
    series = _calls(1)
    with pytest.raises(ValueError):
        run_backtest(series, len(series), lambda h, n: None)
