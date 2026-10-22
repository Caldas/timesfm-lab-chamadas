from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from callcenter_lab.wfm import (
    ConstantAHT,
    ProfileAHT,
    SeriesAHT,
    forecast_aht,
    load_aht_csv,
    synthetic_aht,
    workload_erlangs,
)

INDEX = pd.date_range("2024-03-04 08:00", periods=4, freq="30min")  # Monday 08:00-09:30


def test_constant_aht():
    assert list(ConstantAHT(240).for_index(INDEX)) == [240, 240, 240, 240]
    with pytest.raises(ValueError):
        ConstantAHT(0)


def test_profile_aht_by_weekday_and_hour_with_default():
    table = pd.DataFrame({"weekday": [0], "hour": [9], "aht_seconds": [420.0]})
    values = ProfileAHT(table, default_seconds=300).for_index(INDEX)
    assert list(values) == [300, 300, 420, 420]
    with pytest.raises(ValueError):
        ProfileAHT(pd.DataFrame({"weekday": [0]}), 300)


def test_series_aht_uses_default_outside_the_series():
    series = pd.Series([200.0, 220.0], index=INDEX[:2])
    values = SeriesAHT(series, default_seconds=300).for_index(INDEX)
    assert list(values) == [200, 220, 300, 300]


def test_load_aht_csv_both_formats(tmp_path):
    per_interval = tmp_path / "interval.csv"
    pd.DataFrame({"timestamp": INDEX, "aht_seconds": [1.0, 2.0, 3.0, 4.0]}).to_csv(per_interval, index=False)
    assert list(load_aht_csv(per_interval, 300).for_index(INDEX)) == [1, 2, 3, 4]

    profile = tmp_path / "profile.csv"
    pd.DataFrame({"weekday": [0], "hour": [8], "aht_seconds": [111.0]}).to_csv(profile, index=False)
    assert list(load_aht_csv(profile, 300).for_index(INDEX)) == [111, 111, 300, 300]

    bad = tmp_path / "bad.csv"
    pd.DataFrame({"x": [1]}).to_csv(bad, index=False)
    with pytest.raises(ValueError):
        load_aht_csv(bad, 300)


def test_synthetic_aht_is_reproducible_and_plausible():
    index = pd.date_range("2024-03-04", periods=96, freq="30min")
    a, b = synthetic_aht(index, 300, seed=7), synthetic_aht(index, 300, seed=7)
    assert a.equals(b)
    assert not a.equals(synthetic_aht(index, 300, seed=8))
    assert (a > 0).all() and 200 < a.mean() < 400
    with pytest.raises(ValueError):
        synthetic_aht(index, base_seconds=0)


def test_workload_in_erlangs_for_any_interval():
    # 60 calls x 300 s in 30 minutes = 10 Erlangs; the same calls in 15 minutes = 20 Erlangs
    assert workload_erlangs(60, 300, 30) == pytest.approx(10.0)
    assert workload_erlangs(60, 300, 15) == pytest.approx(20.0)
    assert list(workload_erlangs([0, 30], 300, 30)) == [0, 5]
    with pytest.raises(ValueError):
        workload_erlangs(-1, 300, 30)
    with pytest.raises(ValueError):
        workload_erlangs(1, 300, 0)


def test_forecast_aht_uses_the_model_and_stays_positive():
    class FakeModel:
        def predict(self, history, horizon, return_quantiles, make_positive):
            point = np.full(horizon, -5.0)  # a silly forecast: the AHT must still be positive
            return SimpleNamespace(forecast=point, quantiles=np.stack([point] * 9, axis=1))

    out = forecast_aht(FakeModel(), pd.Series([300.0] * 10), 4)
    assert len(out) == 4 and (out >= 1).all()
