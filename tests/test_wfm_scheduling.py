import numpy as np
import pandas as pd
import pytest

pytest.importorskip("scipy")

from callcenter_lab.wfm import (
    RosterRules,
    ShiftTemplate,
    StaffingConfig,
    build_plan,
    evaluate_roster,
    optimize_roster,
)
from callcenter_lab.wfm.scheduling import (
    effective_agents,
    example_templates,
    format_days,
    parse_days,
    templates_from_table,
    templates_to_table,
)

INTERVAL = 30
WEEKDAYS = (0, 1, 2, 3, 4)


def need_series(per_interval, start="2024-03-04", days=1, window=(8, 16)):
    """The same need during ``window`` (hours) every day, zero otherwise."""
    index = pd.date_range(start, periods=days * 48, freq="30min")
    values = np.zeros(len(index))
    for d in range(days):
        values[d * 48 + window[0] * 2: d * 48 + window[1] * 2] = per_interval
    return pd.Series(values, index=index)


# --- templates ------------------------------------------------------------------------------------


def test_template_validation():
    ShiftTemplate("ok", "08:00", 8)
    for kwargs in (
        {"start": "8:00"}, {"start": "24:00"}, {"hours": 0}, {"hours": 25}, {"days": ()}, {"days": (7,)},
        {"meal_break_minutes": -5}, {"meal_break_minutes": 60, "meal_window_hours": (7.5, 7.9)},
        {"min_people": 3, "max_people": 2}, {"max_on_break_pct": 0}, {"cost_per_hour": -1},
    ):
        with pytest.raises(ValueError):
            ShiftTemplate(**{"name": "x", "start": "08:00", "hours": 8, **kwargs})


def test_days_parsing_and_formatting():
    assert parse_days("seg-sex") == (0, 1, 2, 3, 4)
    assert parse_days("sab, dom") == (5, 6)
    assert parse_days("sex-seg") == (0, 4, 5, 6)  # a range can wrap over the weekend; the result is sorted
    assert format_days((0, 1, 2, 3, 4)) == "seg-sex"
    assert format_days((5,)) == "sab" and format_days((0, 2, 3)) == "seg, qua-qui"
    for text in ("", "xyz", "seg-xyz"):
        with pytest.raises(ValueError):
            parse_days(text)


def test_template_table_roundtrip_and_blank_cells():
    templates = example_templates()
    assert templates_from_table(templates_to_table(templates)) == templates
    table = pd.DataFrame({"nome": ["A", ""], "início": ["09:00", None], "horas": [6, None], "dias": ["seg-sex", None]})
    parsed = templates_from_table(table)
    assert len(parsed) == 1 and parsed[0].start == "09:00" and parsed[0].meal_break_minutes == 0
    with pytest.raises(ValueError):
        templates_from_table(pd.DataFrame({"nome": ["", ""]}))


# --- the optimiser --------------------------------------------------------------------------------


def test_single_shift_covers_a_flat_need_at_minimum_cost():
    need = need_series(3)  # 3 people from 08:00 to 16:00
    roster = optimize_roster(need, [ShiftTemplate("M", "08:00", 8)], INTERVAL, RosterRules(default_cost_per_hour=10))
    assert roster.shifts["people"].tolist() == [3]
    assert roster.cost == pytest.approx(3 * 8 * 10)
    assert roster.coverage["shortfall"].sum() == 0 and roster.coverage["surplus"].sum() == 0
    assert roster.headcount == 3 and roster.status == "ótima"


def test_staggered_shifts_follow_a_changing_need():
    need = need_series(2, window=(8, 12)) + need_series(4, window=(12, 16))
    templates = [ShiftTemplate("A", "08:00", 4), ShiftTemplate("B", "12:00", 4)]
    roster = optimize_roster(need, templates, INTERVAL)
    people = dict(zip(roster.shifts["shift"], roster.shifts["people"]))
    assert people == {"A": 2, "B": 4}
    assert (roster.coverage["covered"] >= roster.coverage["needed"]).all()


def test_meal_breaks_are_staggered_so_coverage_never_dips_below_need():
    need = need_series(2, window=(8, 16))
    template = ShiftTemplate("M", "08:00", 8, meal_break_minutes=60, meal_window_hours=(3.0, 5.0))
    roster = optimize_roster(need, [template], INTERVAL)
    cov = roster.coverage
    assert (cov["covered"] >= cov["needed"]).all() and cov["shortfall"].sum() == 0
    assert roster.shifts["people"].iloc[0] == 3  # 2 at a time on the phones + 1 away for lunch
    assert roster.breaks["people"].sum() == 3
    starts = pd.to_datetime(roster.breaks["break_start"])
    assert (starts >= pd.Timestamp("2024-03-04 11:00")).all() and (starts <= pd.Timestamp("2024-03-04 13:00")).all()


def test_max_on_break_limits_simultaneous_breaks():
    need = need_series(4, window=(8, 16))
    template = ShiftTemplate("M", "08:00", 8, meal_break_minutes=60, meal_window_hours=(3.0, 5.0), max_on_break_pct=50)
    roster = optimize_roster(need, [template], INTERVAL)
    assert (roster.coverage["on_break"] <= 0.5 * roster.coverage["on_shift"] + 1e-9).all()
    assert roster.coverage["shortfall"].sum() == 0


def test_max_people_leaves_a_reported_shortfall():
    need = need_series(5)
    roster = optimize_roster(need, [ShiftTemplate("M", "08:00", 8, max_people=3)], INTERVAL)
    summary = roster.summary()
    assert roster.shifts["people"].tolist() == [3]
    assert summary["shortfall_intervals"] == 16 and summary["shortfall_person_hours"] == pytest.approx(2 * 8)
    assert summary["fully_covered_pct"] == 0.0


def test_min_people_opens_a_shift_with_at_least_that_many():
    need = need_series(1)
    roster = optimize_roster(need, [ShiftTemplate("M", "08:00", 8, min_people=3)], INTERVAL)
    assert roster.shifts["people"].tolist() == [3]


def test_cheaper_template_is_preferred():
    need = need_series(2)
    templates = [ShiftTemplate("caro", "08:00", 8, cost_per_hour=30), ShiftTemplate("barato", "08:00", 8, cost_per_hour=10)]
    roster = optimize_roster(need, templates, INTERVAL)
    assert roster.shifts["shift"].tolist() == ["barato"]


def test_days_off_rule_sets_the_headcount():
    need = need_series(2, days=7)  # 2 people every day for a week
    template = ShiftTemplate("M", "08:00", 8)
    five = optimize_roster(need, [template], INTERVAL, RosterRules(max_days_per_week=5))
    seven = optimize_roster(need, [template], INTERVAL, RosterRules(max_days_per_week=7))
    assert five.headcount == 3 and seven.headcount == 2  # 14 shifts / 5 days = 2.8 -> 3 people
    assert five.coverage["shortfall"].sum() == 0


def test_max_headcount_caps_the_staff_and_reports_the_shortfall():
    need = need_series(2, days=7)
    roster = optimize_roster(need, [ShiftTemplate("M", "08:00", 8)], INTERVAL, RosterRules(max_headcount=2, max_days_per_week=5))
    assert roster.headcount <= 2 and roster.coverage["shortfall"].sum() > 0


def test_template_days_restrict_where_it_is_used():
    need = need_series(2, days=7)  # starts on a Monday
    template = ShiftTemplate("só sábado", "08:00", 8, days=(5,))
    roster = optimize_roster(need, [template], INTERVAL)
    assert set(pd.to_datetime(roster.shifts["date"]).dt.day_of_week) == {5}


def test_overnight_shift_spills_into_the_next_day():
    index = pd.date_range("2024-03-04", periods=96, freq="30min")  # Monday and Tuesday
    need = pd.Series(0.0, index=index)
    need[pd.Timestamp("2024-03-04 23:00"):pd.Timestamp("2024-03-05 02:00")] = 2
    roster = optimize_roster(need, [ShiftTemplate("noite", "22:00", 6)], INTERVAL)
    assert roster.coverage["shortfall"].sum() == 0


def test_no_need_means_an_empty_roster():
    roster = optimize_roster(need_series(0), [ShiftTemplate("M", "08:00", 8)], INTERVAL)
    assert roster.shifts.empty and roster.cost == 0 and roster.summary()["fully_covered_pct"] == 100.0


def test_misaligned_templates_and_bad_input_are_rejected():
    need = need_series(1)
    with pytest.raises(ValueError, match="múltiplo"):
        optimize_roster(need, [ShiftTemplate("x", "08:10", 8)], INTERVAL)
    with pytest.raises(ValueError):
        optimize_roster(need, [], INTERVAL)
    with pytest.raises(ValueError):
        optimize_roster(pd.Series([1, 2]), [ShiftTemplate("x", "08:00", 8)], INTERVAL)
    with pytest.raises(ValueError):
        RosterRules(max_days_per_week=0)


# --- evaluation with the simulator --------------------------------------------------------------


def test_roster_from_a_plan_meets_the_goal_in_the_simulator():
    index = pd.date_range("2024-03-04", periods=96, freq="30min")  # Monday, Tuesday
    hours = index.hour + index.minute / 60
    calls = pd.Series(np.where((hours >= 8) & (hours < 20), 40.0, 0.0), index=index)
    config = StaffingConfig()
    plan = build_plan(calls, config)
    roster = optimize_roster(plan["scheduled"], example_templates(), INTERVAL, RosterRules(default_cost_per_hour=20))
    assert roster.coverage["shortfall"].sum() == 0
    agents = effective_agents(roster, plan, config)
    assert (agents[plan["agents"] > 0] >= plan["agents"][plan["agents"] > 0].to_numpy() - 0).all()
    result = evaluate_roster(roster, plan, config, n_replications=5, seed=1)
    mean, half_width = result.overall["service_level_pct"]
    assert mean + half_width >= config.service_level_pct - 5  # near the goal, within simulation noise
