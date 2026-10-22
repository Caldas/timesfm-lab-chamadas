from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from callcenter_lab.intraday import (
    alert_level,
    deviation_alerts,
    follow_up_day,
    intervals_per_day,
    plan_vs_actual,
)

FREQ = "30min"


class PersistenceModel:
    """Forecasts 'the same as the last 48 intervals' (yesterday), with a +-20% band."""

    def predict(self, history, horizon, return_quantiles, make_positive, **kwargs):
        point = np.resize(np.asarray(history)[-48:], horizon).astype(float)
        return SimpleNamespace(forecast=point, quantiles=np.stack([point * (0.8 + 0.05 * i) for i in range(9)], axis=1))


def daily_pattern():
    hours = np.arange(48) / 2
    return np.where((hours >= 8) & (hours < 20), 40.0, 0.0)


def make_series(days=6, last_day_factor=1.0):
    """``days`` ordinary days and a last one scaled by ``last_day_factor``, 30-minute intervals."""
    index = pd.date_range("2024-03-04", periods=(days + 1) * 48, freq=FREQ)
    values = np.tile(daily_pattern(), days + 1)
    values[-48:] *= last_day_factor
    return pd.Series(values, index=index)


def test_intervals_per_day():
    assert intervals_per_day("30min") == 48 and intervals_per_day("15min") == 96 and intervals_per_day("h") == 24


def test_alert_levels_and_limits():
    assert alert_level(3) == "ok" and alert_level(-9.9) == "ok"
    assert alert_level(10) == "atenção" and alert_level(-15) == "atenção"
    assert alert_level(20) == "crítico" and alert_level(-40) == "crítico"
    assert alert_level(float("nan")) == "ok"
    assert alert_level(12, warn_pct=5, critical_pct=10) == "crítico"
    with pytest.raises(ValueError):
        alert_level(1, warn_pct=0)
    with pytest.raises(ValueError):
        alert_level(1, warn_pct=20, critical_pct=10)


def test_plan_vs_actual_marks_the_position_against_the_band():
    index = pd.date_range("2024-03-04 08:00", periods=4, freq=FREQ)
    planned = pd.DataFrame({"point": [100.0] * 4, "lower": [80.0] * 4, "upper": [120.0] * 4}, index=index)
    actual = pd.Series([100.0, 130.0, 70.0, np.nan], index=index)
    table = plan_vs_actual(planned, actual)
    assert list(table["position"]) == ["dentro", "acima", "abaixo"]  # the interval without data is left out
    assert list(table["difference_pct"]) == [0.0, 30.0, -30.0]


def test_a_zero_plan_has_no_percentage_difference():
    index = pd.date_range("2024-03-04 08:00", periods=1, freq=FREQ)
    planned = pd.DataFrame({"point": [0.0], "lower": [0.0], "upper": [0.0]}, index=index)
    assert np.isnan(plan_vs_actual(planned, pd.Series([5.0], index=index))["difference_pct"].iloc[0])


def _positions_table(positions):
    index = pd.date_range("2024-03-04 08:00", periods=len(positions), freq=FREQ)
    return pd.DataFrame(
        {"point": 100.0, "lower": 80.0, "upper": 120.0, "actual": 100.0, "position": positions}, index=index
    )


def test_isolated_intervals_outside_the_band_are_not_alerts_but_runs_are():
    positions = ["dentro", "acima", "dentro", "acima", "acima", "acima", "dentro", "abaixo", "abaixo", "abaixo", "abaixo"]
    table = _positions_table(positions)
    alerts = deviation_alerts(table, consecutive=3)
    assert list(alerts["position"]) == ["acima", "abaixo"] and list(alerts["intervals"]) == [3, 4]
    assert alerts["start"].iloc[0] == table.index[3] and alerts["end"].iloc[1] == table.index[10]
    assert deviation_alerts(table, consecutive=5).empty
    assert len(deviation_alerts(table, consecutive=1)) == 3  # every separate run counts: 1 + 3 + 4 intervals


def test_a_run_that_switches_side_is_two_runs():
    table = _positions_table(["acima", "acima", "acima", "abaixo", "abaixo", "abaixo"])
    assert list(deviation_alerts(table, 3)["position"]) == ["acima", "abaixo"]


def test_alerts_on_an_empty_table():
    assert deviation_alerts(_positions_table([]), 3).empty
    with pytest.raises(ValueError):
        deviation_alerts(_positions_table(["acima"]), 0)


# --- following a day ----------------------------------------------------------------------------


def test_a_day_that_follows_the_plan_is_ok():
    series = make_series(last_day_factor=1.0)
    day = series.index[-1].normalize()
    result = follow_up_day(PersistenceModel(), series, day, day + pd.Timedelta(hours=12), FREQ)
    assert result.summary["alert"] == "ok" and result.summary["deviation_pct"] == pytest.approx(0)
    assert result.alerts.empty and result.summary["intervals_observed"] == 24
    assert result.summary["plan_total"] == pytest.approx(daily_pattern().sum())


def test_a_day_running_above_plan_raises_an_alert_and_a_projection():
    series = make_series(last_day_factor=1.5)
    day = series.index[-1].normalize()
    result = follow_up_day(PersistenceModel(), series, day, day + pd.Timedelta(hours=14), FREQ)
    summary = result.summary
    assert summary["deviation_pct"] == pytest.approx(50) and summary["alert"] == "crítico"
    assert summary["intervals_above"] > 0 and len(result.alerts) == 1 and result.alerts["position"].iloc[0] == "acima"
    assert summary["projected_total"] > summary["plan_total"]  # actual so far (1.5x) + the rest
    assert summary["projected_difference_pct"] > 0


def test_reforecast_covers_exactly_the_rest_of_the_day():
    series = make_series()
    day = series.index[-1].normalize()
    cutoff = day + pd.Timedelta(hours=10, minutes=30)
    result = follow_up_day(PersistenceModel(), series, day, cutoff, FREQ)
    assert result.reforecast.index[0] == cutoff
    assert result.reforecast.index[-1] == day + pd.Timedelta(hours=23, minutes=30)
    assert len(result.reforecast) == 48 - 21 and len(result.observed) == 21
    assert len(result.plan) == 48


def test_past_day_scores_plan_and_reforecast_on_what_really_happened():
    series = make_series(last_day_factor=1.0)
    day = series.index[-1].normalize()
    result = follow_up_day(PersistenceModel(), series, day, day + pd.Timedelta(hours=12), FREQ)
    assert result.actual_remaining is not None and result.actual_remaining.notna().all()
    for key in ("plan_wape_remaining", "reforecast_wape_remaining", "plan_bias_remaining", "reforecast_bias_remaining"):
        assert key in result.summary and np.isfinite(result.summary[key])


def test_live_day_has_no_actuals_for_the_rest():
    series = make_series(last_day_factor=1.0)
    day = series.index[-1].normalize()
    live = series[series.index < day + pd.Timedelta(hours=12)]  # the data stops at the cutoff
    result = follow_up_day(PersistenceModel(), live, day, day + pd.Timedelta(hours=12), FREQ)
    assert result.actual_remaining is None and "plan_wape_remaining" not in result.summary
    assert "projected_total" in result.summary


def test_cutoff_at_the_end_of_the_day_has_nothing_left_to_forecast():
    series = make_series()
    day = series.index[-1].normalize()
    result = follow_up_day(PersistenceModel(), series, day, day + pd.Timedelta(days=1), FREQ)
    assert result.reforecast is None and "projected_total" not in result.summary


def test_invalid_cutoff_and_missing_history_are_explained():
    series = make_series()
    day = series.index[-1].normalize()
    with pytest.raises(ValueError, match="dentro do dia"):
        follow_up_day(PersistenceModel(), series, day, day + pd.Timedelta(days=2), FREQ)
    first = series.index[0]
    with pytest.raises(ValueError, match="histórico"):
        follow_up_day(PersistenceModel(), series, first.normalize(), first + pd.Timedelta(hours=6), FREQ)
