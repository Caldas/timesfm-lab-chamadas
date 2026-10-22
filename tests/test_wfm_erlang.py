import math

import numpy as np
import pandas as pd
import pytest

from callcenter_lab.wfm import (
    StaffingConfig,
    asa,
    build_plan,
    build_plan_range,
    erlang_a,
    erlang_b,
    erlang_c,
    occupancy,
    required_agents,
    required_agents_erlang_a,
    service_level,
    size_staffing,
)


def erlang_c_textbook(n: int, a: float) -> float:
    """The classic closed form with factorials, as an independent check of the stable recursion."""
    top = (a**n / math.factorial(n)) * (n / (n - a))
    return top / (sum(a**k / math.factorial(k) for k in range(n)) + top)


# --- Erlang B / C -----------------------------------------------------------------------------


def test_erlang_b_known_values():
    assert erlang_b(0, 5) == 1.0
    assert erlang_b(1, 1) == pytest.approx(0.5)  # B(1,1) = 1/2
    assert erlang_b(2, 1) == pytest.approx(0.2)  # B(2,1) = (1/2)/(2!)/(1+1+1/2) = 0.2


@pytest.mark.parametrize("n,a", [(2, 1.0), (5, 3.5), (10, 8.0), (30, 25.0), (60, 55.5)])
def test_erlang_c_matches_the_textbook_formula(n, a):
    assert erlang_c(n, a) == pytest.approx(erlang_c_textbook(n, a), rel=1e-9)


def test_erlang_c_edge_cases():
    assert erlang_c(0, 0) == 0.0
    assert erlang_c(5, 0) == 0.0
    assert erlang_c(3, 3) == 1.0  # load equal to agents: always waits
    assert erlang_c(2, 5) == 1.0  # overloaded
    with pytest.raises(ValueError):
        erlang_c(-1, 1)


def test_erlang_c_is_stable_for_large_loads():
    value = erlang_c(1200, 1150.0)
    assert 0 < value < 1 and math.isfinite(value)


def test_more_agents_means_better_service():
    load, aht = 20.0, 300.0
    levels = [service_level(n, load, aht, 20) for n in range(21, 40)]
    waits = [asa(n, load, aht) for n in range(21, 40)]
    assert levels == sorted(levels)  # non-decreasing
    assert waits == sorted(waits, reverse=True)
    assert all(0 <= x <= 1 for x in levels)


def test_service_level_limits():
    assert service_level(5, 0, 300, 20) == 1.0
    assert service_level(4, 4, 300, 20) == 0.0
    assert service_level(10, 5, 300, 10_000) == pytest.approx(1.0, abs=1e-9)
    assert asa(5, 0, 300) == 0.0
    assert asa(3, 3, 300) == math.inf
    assert occupancy(10, 8) == pytest.approx(0.8)
    assert occupancy(0, 0) == 0.0


# --- required agents --------------------------------------------------------------------------


def test_required_agents_meets_goal_and_is_minimal():
    load, aht = 15.0, 240.0
    n = required_agents(load, aht, 80, 20)
    assert service_level(n, load, aht, 20) >= 0.8
    assert service_level(n - 1, load, aht, 20) < 0.8


def test_required_agents_respects_occupancy_cap_and_asa():
    load, aht = 30.0, 300.0
    base = required_agents(load, aht, 50, 120)  # lax goal
    capped = required_agents(load, aht, 50, 120, max_occupancy_pct=60)
    assert capped >= math.ceil(load / 0.6) and capped >= base
    with_asa = required_agents(load, aht, 50, 120, max_asa_seconds=5)
    assert asa(with_asa, load, aht) <= 5


def test_required_agents_zero_load_and_errors():
    assert required_agents(0, 300, 80, 20) == 0
    with pytest.raises(ValueError):
        required_agents(-1, 300, 80, 20)
    with pytest.raises(ValueError):
        required_agents(10, 300, 80, 20, max_agents=5)


def test_required_agents_grow_with_load_and_goal():
    sizes = [required_agents(a, 300, 80, 20) for a in (1, 5, 10, 20, 50, 100)]
    assert sizes == sorted(sizes)
    assert required_agents(20, 300, 95, 20) >= required_agents(20, 300, 70, 20)


# --- Erlang A ---------------------------------------------------------------------------------


def test_erlang_a_with_very_patient_callers_matches_erlang_c():
    n, load, aht = 12, 10.0, 300.0
    r = erlang_a(n, load, aht, patience_seconds=1e7, threshold_seconds=20)
    assert r["abandon_prob"] == pytest.approx(0, abs=1e-3)
    assert r["prob_wait"] == pytest.approx(erlang_c(n, load), abs=2e-3)
    assert r["service_level"] == pytest.approx(service_level(n, load, aht, 20), abs=3e-3)
    assert r["avg_wait_seconds"] == pytest.approx(asa(n, load, aht), rel=0.02)


def test_erlang_a_abandonment_grows_when_patience_shrinks():
    args = (8, 10.0, 300.0)  # under-staffed on purpose
    short = erlang_a(*args, patience_seconds=30, threshold_seconds=20)["abandon_prob"]
    long = erlang_a(*args, patience_seconds=600, threshold_seconds=20)["abandon_prob"]
    assert 0 <= long < short <= 1


def test_erlang_a_edge_cases():
    assert erlang_a(5, 0, 300, 60, 20)["service_level"] == 1.0
    assert erlang_a(0, 5, 300, 60, 20)["abandon_prob"] == 1.0
    with pytest.raises(ValueError):
        erlang_a(5, 3, 300, 0, 20)


def test_erlang_a_needs_no_more_agents_than_erlang_c():
    load, aht = 12.0, 300.0
    a = required_agents_erlang_a(load, aht, 60, 80, 20)
    c = required_agents(load, aht, 80, 20)
    assert 1 <= a <= c


# --- the whole chain --------------------------------------------------------------------------


def _calls(values, freq="30min"):
    return pd.Series(values, index=pd.date_range("2024-03-04 08:00", periods=len(values), freq=freq))


def test_size_staffing_columns_and_zero_intervals():
    cfg = StaffingConfig()
    out = size_staffing([0.0, 8.0, 20.0], 300.0, cfg)
    assert out["agents"].iloc[0] == 0
    assert out["agents"].is_monotonic_increasing
    assert (out["service_level_pct"] >= cfg.service_level_pct - 1e-6).all()
    assert (out["occupancy_pct"] <= cfg.max_occupancy_pct + 1e-6).all()
    assert (out["scheduled"] >= out["agents"]).all()


def test_build_plan_workload_and_cost():
    cfg = StaffingConfig(cost_per_hour=20.0)
    plan = build_plan(_calls([0, 60, 120]), cfg)
    # 60 calls x 300 s / 1800 s = 10 Erlangs
    assert plan["workload_erlangs"].iloc[1] == pytest.approx(10.0)
    assert plan["agents"].iloc[0] == 0 and plan["agents"].iloc[2] > plan["agents"].iloc[1]
    assert plan["cost"].iloc[1] == pytest.approx(plan["scheduled"].iloc[1] * 0.5 * 20)


def test_build_plan_rejects_a_mismatched_interval():
    with pytest.raises(ValueError, match="intervalo"):
        build_plan(_calls([10, 20], freq="h"), StaffingConfig(interval_minutes=30))
    with pytest.raises(TypeError):
        build_plan(pd.Series([1, 2, 3]), StaffingConfig())


def test_build_plan_uses_erlang_a_when_patience_is_set():
    calls = _calls([40, 80])
    patient = build_plan(calls, StaffingConfig())
    impatient = build_plan(calls, StaffingConfig(mean_patience_seconds=60))
    assert (impatient["agents"] <= patient["agents"]).all()
    assert (impatient["abandon_pct"] >= 0).all()


def test_build_plan_range_orders_low_expected_high():
    point = _calls([50, 100])
    out = build_plan_range(point, point * 0.8, point * 1.3, StaffingConfig())
    assert (out["agents_low"] <= out["agents_expected"]).all()
    assert (out["agents_expected"] <= out["agents_high"]).all()
    assert np.isfinite(out.to_numpy()).all()
