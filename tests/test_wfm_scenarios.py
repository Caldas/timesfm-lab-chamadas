import numpy as np
import pandas as pd
import pytest

pytest.importorskip("scipy")

from callcenter_lab.wfm import (
    SENSITIVITY_PARAMETERS,
    Scenario,
    ShrinkageConfig,
    StaffingConfig,
    apply_scenario,
    example_scenarios,
    optimize_roster,
    run_scenarios,
    sensitivity,
)
from callcenter_lab.wfm.scenarios import adjust_shrinkage, scenarios_from_table, scenarios_to_table
from callcenter_lab.wfm.scheduling import RosterRules, example_templates


@pytest.fixture
def volumes():
    index = pd.date_range("2024-03-04", periods=96, freq="30min")  # Monday and Tuesday
    hours = index.hour + index.minute / 60
    expected = pd.Series(np.where((hours >= 8) & (hours < 20), 40.0, 0.0), index=index)
    return {"low": expected * 0.8, "expected": expected, "high": expected * 1.3}


def test_scenario_validation():
    with pytest.raises(ValueError):
        Scenario("")
    with pytest.raises(ValueError):
        Scenario("x", volume="enorme")
    with pytest.raises(ValueError):
        Scenario("x", volume_factor=0)
    with pytest.raises(ValueError):
        Scenario("x", aht_factor=-1)


def test_adjust_shrinkage_adds_points_in_proportion():
    base = ShrinkageConfig(10, 3, 5, 5, 2)  # 25%
    more = adjust_shrinkage(base, 5)
    assert more.total_pct == pytest.approx(30)
    assert more.pauses_pct / more.absenteeism_pct == pytest.approx(base.pauses_pct / base.absenteeism_pct)
    assert adjust_shrinkage(base, 0) is base
    assert adjust_shrinkage(ShrinkageConfig(0, 0, 0, 0, 0), 4).other_pct == 4
    assert adjust_shrinkage(base, -5).total_pct == pytest.approx(20)
    for bad in (-30, 80):
        with pytest.raises(ValueError):
            adjust_shrinkage(base, bad)


def test_apply_scenario_overrides_only_what_is_set():
    config = StaffingConfig()
    changed = apply_scenario(Scenario("x", service_level_pct=95, mean_patience_seconds=90), config)
    assert changed.service_level_pct == 95 and changed.mean_patience_seconds == 90
    assert changed.service_level_seconds == config.service_level_seconds and changed.shrinkage == config.shrinkage


def test_run_scenarios_orders_the_effects_as_expected(volumes):
    config = StaffingConfig(cost_per_hour=20)
    result = run_scenarios(volumes, example_scenarios(), config).set_index("scenario")
    base = result.loc["Base"]
    assert base["delta_agent_hours"] == 0 and base["delta_cost"] == 0
    assert result.loc["Volume alto (90%)", "agent_hours"] > base["agent_hours"] > result.loc["Volume baixo (10%)", "agent_hours"]
    assert result.loc["Volume +10%", "agent_hours"] > base["agent_hours"]
    assert result.loc["TMA +10%", "agent_hours"] > base["agent_hours"]
    assert result.loc["Meta 90% em 20 s", "agent_hours"] > base["agent_hours"]
    # more absenteeism does not change the agents needed on the phones, only the people to schedule
    assert result.loc["Absenteísmo +5 pontos", "agent_hours"] == pytest.approx(base["agent_hours"])
    assert result.loc["Absenteísmo +5 pontos", "scheduled_hours"] > base["scheduled_hours"]
    assert (result["cost"] > 0).all() and result.loc["Volume alto (90%)", "delta_cost"] > 0


def test_run_scenarios_without_cost_leaves_cost_empty(volumes):
    result = run_scenarios(volumes, [Scenario("Base")], StaffingConfig())
    assert result["cost"].isna().all()


def test_scenario_needing_the_forecast_range_is_explained(volumes):
    with pytest.raises(ValueError, match="previsão"):
        run_scenarios({"expected": volumes["expected"]}, [Scenario("Base"), Scenario("alto", volume="high")], StaffingConfig())
    with pytest.raises(ValueError):
        run_scenarios(volumes, [], StaffingConfig())


def test_a_fixed_roster_shows_shortfall_when_volume_grows(volumes):
    from callcenter_lab.wfm import build_plan

    config = StaffingConfig()
    plan = build_plan(volumes["expected"], config)
    roster = optimize_roster(plan["scheduled"], example_templates(), 30, RosterRules())
    scenarios = [Scenario("Base"), Scenario("Volume alto (90%)", volume="high")]
    result = run_scenarios(volumes, scenarios, config, roster=roster).set_index("scenario")
    assert result.loc["Base", "roster_shortfall_person_hours"] == 0
    assert result.loc["Volume alto (90%)", "roster_shortfall_person_hours"] > 0
    assert result.loc["Volume alto (90%)", "roster_shortfall_intervals"] > 0


def test_sensitivity_for_each_parameter(volumes):
    config = StaffingConfig(cost_per_hour=10)
    calls = volumes["expected"]
    volume = sensitivity(calls, config, "volume_factor")
    assert list(volume["agent_hours"]) == sorted(volume["agent_hours"])  # more calls, never fewer agents
    neutral = volume[volume["value"] == 1.0].iloc[0]
    assert neutral["delta_agent_hours_pct"] == pytest.approx(0)
    shrink = sensitivity(calls, config, "shrinkage_pp")
    assert shrink["agent_hours"].nunique() == 1  # shrinkage only changes who is scheduled
    assert list(shrink["scheduled_hours"]) == sorted(shrink["scheduled_hours"])
    custom = sensitivity(calls, config, "aht_factor", values=[1.0, 1.2])
    assert len(custom) == 2 and custom["agent_hours"].iloc[1] > custom["agent_hours"].iloc[0]
    for parameter in SENSITIVITY_PARAMETERS:
        assert len(sensitivity(calls, config, parameter)) == len(SENSITIVITY_PARAMETERS[parameter][1])
    with pytest.raises(ValueError):
        sensitivity(calls, config, "cor_do_telefone")


def test_scenarios_table_roundtrip_and_blank_cells():
    scenarios = example_scenarios()
    assert scenarios_from_table(scenarios_to_table(scenarios)) == scenarios
    table = pd.DataFrame({"nome": ["Só nome", ""], "volume": ["alto", None], "fator_volume": [None, None]})
    parsed = scenarios_from_table(table)
    assert len(parsed) == 1 and parsed[0].volume == "high" and parsed[0].volume_factor == 1.0
    with pytest.raises(ValueError):
        scenarios_from_table(pd.DataFrame({"nome": ["x"], "volume": ["gigante"]}))
    with pytest.raises(ValueError):
        scenarios_from_table(pd.DataFrame({"nome": [""]}))
