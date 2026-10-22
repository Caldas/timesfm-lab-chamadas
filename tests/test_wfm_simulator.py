import numpy as np
import pandas as pd
import pytest

from callcenter_lab.wfm import StaffingConfig, asa, erlang_a, generate_dataset, service_level
from callcenter_lab.wfm.simulator import overall_metrics, simulate, simulate_replications

INTERVAL = 30  # minutes


def steady(n_intervals, load, aht=300.0):
    """Expected calls per interval that give ``load`` Erlangs."""
    return np.full(n_intervals, load * INTERVAL * 60 / aht)


def test_plenty_of_agents_answers_everything_at_once():
    out = simulate(steady(6, 5), 40, 300, INTERVAL, seed=1).intervals
    assert (out["service_level_pct"] > 99).all()
    assert out["abandoned"].sum() == 0
    assert out["answered"].sum() == out["offered"].sum()


def test_no_agents_means_nobody_is_answered():
    patient = simulate(steady(3, 5), 0, 300, INTERVAL, seed=1).intervals
    assert patient["answered"].sum() == 0 and patient["abandoned"].sum() == 0  # they wait forever
    impatient = simulate(steady(3, 5), 0, 300, INTERVAL, mean_patience_seconds=30, seed=1).intervals
    assert impatient["answered"].sum() == 0
    assert impatient["abandoned"].sum() == impatient["offered"].sum()
    assert (impatient["abandon_pct"] == 100).all()


def test_calls_wait_until_agents_arrive():
    agents = [0, 0, 30, 30]
    out = simulate(steady(4, 3), agents, 300, INTERVAL, seed=2, record_calls=True)
    first = out.calls[out.calls["interval"] == 0]
    assert (first["wait_seconds"] > 0).all()  # no agent before the third interval
    assert first["answered"].all()
    assert out.intervals["service_level_pct"].iloc[0] < 5


def test_same_seed_same_result_different_seed_different_result():
    args = (steady(8, 8), 10, 300, INTERVAL)
    a = simulate(*args, seed=5).intervals
    assert a.equals(simulate(*args, seed=5).intervals)
    assert not a.equals(simulate(*args, seed=6).intervals)


def test_arrivals_are_poisson_around_the_expected_volume():
    out = simulate(np.full(400, 50.0), 80, 120, INTERVAL, seed=3).intervals
    assert out["offered"].mean() == pytest.approx(50, rel=0.03)
    assert out["offered"].var() == pytest.approx(50, rel=0.3)  # Poisson: variance ~ mean


def test_occupancy_is_close_to_load_over_agents():
    out = simulate(steady(40, 10), 12, 300, INTERVAL, seed=4).intervals.iloc[4:]
    assert out["occupancy_pct"].mean() == pytest.approx(100 * 10 / 12, abs=4)


def test_interval_metrics_have_consistent_totals():
    out = simulate(steady(10, 9), 10, 300, INTERVAL, mean_patience_seconds=60, seed=7).intervals
    assert ((out["answered"] + out["abandoned"]) <= out["offered"]).all()
    assert out["service_level_pct"].between(0, 100).all()


def test_input_validation():
    with pytest.raises(ValueError):
        simulate([], 1, 300, INTERVAL)
    with pytest.raises(ValueError):
        simulate([-1], 1, 300, INTERVAL)
    with pytest.raises(ValueError):
        simulate([10], -1, 300, INTERVAL)
    with pytest.raises(ValueError):
        simulate([10], 1, 300, INTERVAL, mean_patience_seconds=0)
    with pytest.raises(ValueError):
        simulate([10], 1, 300, INTERVAL, aht_cv=0)


def test_zero_calls_everywhere_is_fine():
    out = simulate(np.zeros(3), 5, 300, INTERVAL).intervals
    assert out["offered"].sum() == 0 and out["service_level_pct"].isna().all()
    assert (out["occupancy_pct"] == 0).all()


def test_lognormal_service_times_keep_the_mean():
    out = simulate(np.full(60, 80.0), 100, 300, INTERVAL, aht_cv=0.6, seed=8, record_calls=True)
    assert out.calls["handle_seconds"].mean() == pytest.approx(300, rel=0.05)


# --- replications -----------------------------------------------------------------------------


def test_replications_report_means_and_confidence_intervals():
    result = simulate_replications(steady(12, 8), 10, 300, INTERVAL, n_replications=6, seed=11, warmup_intervals=2)
    assert result.n_replications == 6
    assert {"service_level_pct", "service_level_pct_ci"} <= set(result.intervals.columns)
    mean, half = result.overall["service_level_pct"]
    assert 0 <= mean <= 100 and half >= 0
    again = simulate_replications(steady(12, 8), 10, 300, INTERVAL, n_replications=6, seed=11, warmup_intervals=2)
    assert again.overall == result.overall  # reproducible
    with pytest.raises(ValueError):
        simulate_replications(steady(2, 1), 2, 300, INTERVAL, n_replications=0)


# --- cross-validation: Erlang formulas against the simulator ----------------------------------


def test_erlang_c_service_level_and_wait_match_the_simulation():
    n, load, aht = 12, 10.0, 300.0
    result = simulate_replications(steady(40, load, aht), n, aht, INTERVAL, n_replications=10, seed=100, warmup_intervals=4)
    sim_sl, _ = result.overall["service_level_pct"]
    assert sim_sl == pytest.approx(100 * service_level(n, load, aht, 20), abs=3.0)  # documented tolerance: 3 p.p.
    sim_wait, _ = result.overall["avg_wait_answered_seconds"]
    assert sim_wait == pytest.approx(asa(n, load, aht), rel=0.2)


def test_erlang_a_abandonment_and_service_level_match_the_simulation():
    n, load, aht, patience = 9, 10.0, 300.0, 60.0
    model = erlang_a(n, load, aht, patience, 20)
    result = simulate_replications(
        steady(40, load, aht), n, aht, INTERVAL, n_replications=10, seed=200, warmup_intervals=4,
        mean_patience_seconds=patience,
    )
    assert result.overall["abandon_pct"][0] == pytest.approx(100 * model["abandon_prob"], abs=2.0)
    assert result.overall["service_level_pct"][0] == pytest.approx(100 * model["service_level"], abs=3.0)


# --- synthetic data ---------------------------------------------------------------------------


def test_generate_dataset_is_reproducible_and_complete():
    index = pd.date_range("2024-03-04 08:00", periods=24, freq="30min")
    calls = pd.Series(np.linspace(20, 90, 24), index=index)
    cfg = StaffingConfig(mean_patience_seconds=90)
    a = generate_dataset(calls, cfg, seed=3)
    b = generate_dataset(calls, cfg, seed=3)
    assert a.equals(b)
    assert list(a.columns[:7]) == [
        "timestamp", "calls_offered", "calls_answered", "calls_abandoned",
        "aht_seconds", "avg_wait_seconds", "service_level_pct",
    ]
    assert len(a) == 24 and (a["calls_answered"] + a["calls_abandoned"] <= a["calls_offered"]).all()
    assert overall_metrics(simulate(calls.to_numpy(), a["agents"], 300, 30, seed=3).intervals)["service_level_pct"] > 50
