import numpy as np
import pandas as pd
import pytest

from callcenter_lab.loading import detect_columns, detect_queue_column, split_by_queue
from callcenter_lab.synthetic import QUEUE_AHT_SECONDS, make_synthetic_calls_by_queue
from callcenter_lab.wfm import StaffingConfig, build_queue_plans, compare_pooling, pooled_plan
from callcenter_lab.wfm.queues import queue_config


def day_of_calls(day="2024-03-04"):
    """A weekday of the example queues (30-minute intervals)."""
    df = make_synthetic_calls_by_queue(weeks=2)
    return {
        name: series.loc[day]
        for name, series in split_by_queue(df, "timestamp", "calls_offered", "queue", "30min").items()
    }


# --- loading ----------------------------------------------------------------------------------------


def test_detect_queue_column_and_split():
    df = make_synthetic_calls_by_queue(weeks=1)
    date_col, value_col = detect_columns(df)
    assert (date_col, value_col) == ("timestamp", "calls_offered")
    assert detect_queue_column(df, date_col, value_col) == "queue"
    series = split_by_queue(df, date_col, value_col, "queue", "30min")
    assert list(series) == ["vendas", "suporte", "cobrança"]
    lengths = {len(s) for s in series.values()}
    assert len(lengths) == 1  # all queues cover the same period
    assert series["suporte"].sum() == df[df["queue"] == "suporte"]["calls_offered"].sum()


def test_no_queue_column_in_a_single_queue_file():
    df = pd.DataFrame({"timestamp": pd.date_range("2024-03-04", periods=4, freq="30min"), "calls_offered": [1, 2, 3, 4]})
    assert detect_queue_column(df, "timestamp", "calls_offered") is None
    with pytest.raises(ValueError, match="não existe"):
        split_by_queue(df, "timestamp", "calls_offered", "fila", "30min")


def test_queues_with_different_periods_are_aligned_with_zeros():
    df = pd.DataFrame({
        "timestamp": list(pd.date_range("2024-03-04 08:00", periods=2, freq="30min")) + [pd.Timestamp("2024-03-04 09:00")],
        "queue": ["a", "a", "b"], "calls_offered": [5, 6, 7],
    })
    series = split_by_queue(df, "timestamp", "calls_offered", "queue", "30min")
    assert list(series["a"]) == [5, 6, 0] and list(series["b"]) == [0, 0, 7]


# --- independent sizing -----------------------------------------------------------------------------


def test_each_queue_is_sized_on_its_own_and_the_total_is_their_sum():
    calls = day_of_calls()
    plans = build_queue_plans(calls, StaffingConfig(), QUEUE_AHT_SECONDS)
    assert set(plans.plans) == set(calls)
    assert (plans.total["agents"] == sum(p["agents"] for p in plans.plans.values())).all()
    assert (plans.total["scheduled"] == sum(p["scheduled"] for p in plans.plans.values())).all()
    summary = plans.summary()
    assert list(summary.index) == ["vendas", "suporte", "cobrança", "Total"]
    assert summary.loc["Total", "agent_hours"] == pytest.approx(summary.loc[["vendas", "suporte", "cobrança"], "agent_hours"].sum())
    assert (plans.total["agents_suporte"] == plans.plans["suporte"]["agents"]).all()


def test_a_longer_handling_time_needs_more_agents():
    calls = day_of_calls()
    short = build_queue_plans(calls, StaffingConfig(), {"vendas": 200, "suporte": 200, "cobrança": 200})
    long = build_queue_plans(calls, StaffingConfig(), {"vendas": 400, "suporte": 400, "cobrança": 400})
    assert long.total["agents"].sum() > short.total["agents"].sum()
    assert queue_config(StaffingConfig(), 123).aht_seconds == 123
    with pytest.raises(ValueError):
        build_queue_plans({}, StaffingConfig())


# --- pooling ----------------------------------------------------------------------------------------


def test_a_cross_trained_team_needs_no_more_agents_than_separate_teams():
    calls = day_of_calls()
    config = StaffingConfig()
    separate = build_queue_plans(calls, config, QUEUE_AHT_SECONDS)
    pooled = pooled_plan(calls, config, QUEUE_AHT_SECONDS)
    assert (pooled["agents"] <= separate.total["agents"]).all()
    assert pooled["agents"].sum() < separate.total["agents"].sum()  # strictly fewer over the day
    expected_load = sum(calls[n].to_numpy() * QUEUE_AHT_SECONDS[n] / config.interval_seconds for n in calls)
    assert np.allclose(pooled["workload_erlangs"], expected_load)


def test_comparing_separate_and_cross_trained_teams_by_simulation():
    calls = {name: series.iloc[16:40] for name, series in day_of_calls().items()}  # 08:00 to 20:00
    config = StaffingConfig()
    result = compare_pooling(calls, config, QUEUE_AHT_SECONDS, n_replications=6, seed=1)
    summary = result.summary
    assert list(summary.index) == ["Equipes separadas", "Equipe cruzada"]
    assert summary.loc["Equipe cruzada", "agent_hours"] < summary.loc["Equipes separadas", "agent_hours"]
    assert summary.loc["Equipe cruzada", "agent_hours_vs_separate_pct"] < 0
    assert summary.loc["Equipes separadas", "agent_hours_vs_separate_pct"] == 0
    for design in summary.index:  # both designs are sized for the same goal: neither is far below it
        assert summary.loc[design, "min_service_level_pct"] > config.service_level_pct - 12
    assert len(result.per_queue) == 6 and set(result.per_queue["design"]) == set(summary.index)
    assert list(result.agents.columns) == ["Equipes separadas", "Equipe cruzada"]
    assert result.separate.n_replications == 6
