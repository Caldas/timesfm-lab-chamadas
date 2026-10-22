import numpy as np
import pandas as pd
import pytest

from callcenter_lab.wfm import (
    AgentGroup,
    QueueSpec,
    overall_by_queue,
    service_level,
    simulate_skills,
    simulate_skills_replications,
)

INTERVAL = 30


def steady(n_intervals, load, aht=300.0):
    """Expected calls per interval that give ``load`` Erlangs."""
    return np.full(n_intervals, load * INTERVAL * 60 / aht)


def spec(name, aht=300.0, patience=None, threshold=20.0, priority=0):
    return QueueSpec(name, aht, patience, threshold, priority)


# --- validation -------------------------------------------------------------------------------------


def test_queue_and_group_validation():
    with pytest.raises(ValueError):
        QueueSpec("", 300)
    with pytest.raises(ValueError):
        QueueSpec("a", 0)
    with pytest.raises(ValueError):
        QueueSpec("a", 300, mean_patience_seconds=0)
    with pytest.raises(ValueError):
        AgentGroup("g", (), 5)
    with pytest.raises(ValueError):
        AgentGroup("g", ("a",), -1)


def test_inconsistent_inputs_are_rejected():
    calls = {"a": steady(4, 3)}
    group = AgentGroup("g", ("a",), 5)
    with pytest.raises(ValueError, match="mesmas filas"):
        simulate_skills({"b": steady(4, 3)}, [group], [spec("a")], INTERVAL)
    with pytest.raises(ValueError, match="não existem"):
        simulate_skills(calls, [AgentGroup("g", ("zzz",), 5)], [spec("a")], INTERVAL)
    with pytest.raises(ValueError):
        simulate_skills(calls, [], [spec("a")], INTERVAL)
    with pytest.raises(ValueError):
        simulate_skills(calls, [group], [spec("a"), spec("a")], INTERVAL)
    with pytest.raises(ValueError):
        simulate_skills({"a": steady(4, 3), "b": steady(3, 3)}, [AgentGroup("g", ("a", "b"), 5)], [spec("a"), spec("b")], INTERVAL)
    with pytest.raises(ValueError):
        simulate_skills(calls, [group], [spec("a")], INTERVAL, routing="aleatório")


# --- behaviour ----------------------------------------------------------------------------------------


def test_one_queue_one_group_matches_erlang_c():
    """With a single queue the simulator must agree with the formula (the skills code is a generalisation)."""
    n, load = 12, 10.0
    result = simulate_skills_replications(
        {"a": steady(40, load)}, [AgentGroup("g", ("a",), n)], [spec("a")], INTERVAL,
        n_replications=10, seed=100, warmup_intervals=4,
    )
    sim_sl = result.queues["a"]["service_level_pct"][0]
    assert sim_sl == pytest.approx(100 * service_level(n, load, 300, 20), abs=3.0)
    assert 0 < result.occupancy_pct["g"][0] <= 100


def test_a_queue_nobody_can_answer_is_never_served():
    calls = {"a": steady(6, 3), "b": steady(6, 3)}
    groups = [AgentGroup("só a", ("a",), 10)]
    queues = [spec("a"), spec("b", patience=60)]
    result = simulate_skills(calls, groups, queues, INTERVAL, seed=1)
    assert result.queues["a"]["answered"].sum() > 0 and result.queues["a"]["service_level_pct"].mean() > 90
    assert result.queues["b"]["answered"].sum() == 0
    assert result.queues["b"]["abandoned"].sum() == result.queues["b"]["offered"].sum()  # all hung up


def test_pooling_the_same_agents_improves_the_service_level():
    """Two equal queues of 8 Erlangs: 9+9 agents in separate teams against 18 agents who answer both."""
    calls = {"a": steady(40, 8), "b": steady(40, 8)}
    queues = [spec("a"), spec("b")]
    common = {"n_replications": 10, "seed": 5, "warmup_intervals": 4}
    separate = simulate_skills_replications(
        calls, [AgentGroup("A", ("a",), 9), AgentGroup("B", ("b",), 9)], queues, INTERVAL, **common
    )
    pooled = simulate_skills_replications(calls, [AgentGroup("todos", ("a", "b"), 18)], queues, INTERVAL, **common)
    separate_sl = np.mean([separate.queues[q]["service_level_pct"][0] for q in "ab"])
    pooled_sl = np.mean([pooled.queues[q]["service_level_pct"][0] for q in "ab"])
    assert pooled_sl > separate_sl + 3  # a clear gain: the Erlang formula for one queue cannot see it


def test_priority_routing_serves_the_important_queue_first():
    calls = {"a": steady(40, 4), "b": steady(40, 4)}
    groups = [AgentGroup("todos", ("a", "b"), 8)]  # tight: 8 agents for 8 Erlangs in total
    queues = [spec("a", priority=0), spec("b", priority=1)]
    common = {"n_replications": 8, "seed": 9, "warmup_intervals": 4}
    prioritised = simulate_skills_replications(calls, groups, queues, INTERVAL, routing="priority", **common)
    fair = simulate_skills_replications(calls, groups, queues, INTERVAL, routing="longest_wait", **common)
    assert prioritised.queues["a"]["service_level_pct"][0] > prioritised.queues["b"]["service_level_pct"][0] + 10
    assert abs(fair.queues["a"]["service_level_pct"][0] - fair.queues["b"]["service_level_pct"][0]) < 8


def test_preference_decides_who_answers_first_when_both_are_free():
    calls = {"a": steady(20, 1)}  # light load: someone is nearly always free
    groups = [AgentGroup("especialistas", ("a",), 4), AgentGroup("cruzados", ("a", "b"), 4)]
    queues = [spec("a"), spec("b")]
    calls["b"] = steady(20, 0.01)
    specialist_first = simulate_skills(calls, groups, queues, INTERVAL, prefer="specialist", seed=3)
    generalist_first = simulate_skills(calls, groups, queues, INTERVAL, prefer="generalist", seed=3)
    assert specialist_first.occupancy_pct["especialistas"].mean() > specialist_first.occupancy_pct["cruzados"].mean()
    assert generalist_first.occupancy_pct["cruzados"].mean() > generalist_first.occupancy_pct["especialistas"].mean()


def test_calls_wait_until_the_group_has_agents():
    calls = {"a": steady(4, 3)}
    result = simulate_skills(calls, [AgentGroup("g", ("a",), [0, 0, 20, 20])], [spec("a")], INTERVAL, seed=2)
    first = result.queues["a"]
    assert first["service_level_pct"].iloc[0] < 5 and first["answered"].iloc[0] == first["offered"].iloc[0]  # served later
    assert list(result.agents["g"]) == [0, 0, 20, 20]


def test_same_seed_same_result_and_overall_summary():
    args = ({"a": steady(8, 5), "b": steady(8, 3)}, [AgentGroup("g", ("a", "b"), 10)], [spec("a"), spec("b", 240)], INTERVAL)
    first = simulate_skills(*args, seed=7)
    again = simulate_skills(*args, seed=7)
    assert all(first.queues[q].equals(again.queues[q]) for q in "ab")
    table = overall_by_queue(first)
    assert list(table.index) == ["a", "b"] and (table["offered"] > 0).all()
    assert table["service_level_pct"].between(0, 100).all()
    assert (first.queues["b"]["avg_handle_seconds"].dropna() > 0).all()


def test_zero_calls_is_fine_and_index_is_kept():
    index = pd.date_range("2024-03-04", periods=3, freq="30min")
    result = simulate_skills({"a": np.zeros(3)}, [AgentGroup("g", ("a",), 2)], [spec("a")], INTERVAL, index=index)
    assert result.queues["a"]["offered"].sum() == 0 and result.queues["a"].index.equals(index)
    assert np.isnan(overall_by_queue(result).loc["a", "service_level_pct"])
