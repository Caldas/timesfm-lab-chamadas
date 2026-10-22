import numpy as np
import pandas as pd
import pytest

from callcenter_lab.wfm import (
    PRESETS,
    ShrinkageConfig,
    StaffingConfig,
    daily_summary,
    preset,
    scheduled_headcount,
    shrinkage_for_index,
    shrinkage_from_hours,
)

# --- StaffingConfig ---------------------------------------------------------------------------


def test_defaults_are_valid():
    cfg = StaffingConfig()
    assert cfg.interval_minutes == 30
    assert cfg.interval_seconds == 1800
    assert cfg.shrinkage.total_pct == 25.0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"interval_minutes": 7},
        {"service_level_pct": 0},
        {"service_level_pct": 101},
        {"service_level_seconds": -1},
        {"max_occupancy_pct": 0},
        {"max_occupancy_pct": 120},
        {"max_asa_seconds": -5},
        {"mean_patience_seconds": 0},
        {"aht_seconds": 0},
        {"cost_per_hour": -1},
        {"shift_hours": 0},
    ],
)
def test_invalid_values_are_rejected_with_a_clear_message(kwargs):
    with pytest.raises(ValueError):
        StaffingConfig(**kwargs)


def test_config_roundtrip_through_a_file(tmp_path):
    cfg = StaffingConfig(
        interval_minutes=15, service_level_pct=90, service_level_seconds=30,
        mean_patience_seconds=120, cost_per_hour=25.5,
        shrinkage=ShrinkageConfig(pauses_pct=12, training_pct=1, absenteeism_pct=4, vacation_pct=6, other_pct=0),
    )
    path = tmp_path / "config.json"
    cfg.save(path)
    assert StaffingConfig.load(path) == cfg


def test_unknown_keys_are_rejected():
    with pytest.raises(ValueError, match="desconhecido"):
        StaffingConfig.from_dict({"intervalo": 30})


def test_presets_are_valid_examples():
    assert set(PRESETS) == {"80-20", "90-30"}
    assert preset("90-30").service_level_seconds == 30
    with pytest.raises(ValueError):
        preset("nao-existe")


# --- Shrinkage --------------------------------------------------------------------------------


def test_shrinkage_total_and_limits():
    assert ShrinkageConfig(10, 0, 0, 0, 0).total_pct == 10
    with pytest.raises(ValueError):
        ShrinkageConfig(pauses_pct=-1)
    with pytest.raises(ValueError):
        ShrinkageConfig(pauses_pct=60, training_pct=40)  # sums to 100


def test_shrinkage_from_hours():
    cfg = shrinkage_from_hours(160, pauses=16, training=8, absenteeism=8, vacation=0, other=0)
    assert cfg.pauses_pct == pytest.approx(10)
    assert cfg.total_pct == pytest.approx(20)
    with pytest.raises(ValueError):
        shrinkage_from_hours(160, coffee=3)
    with pytest.raises(ValueError):
        shrinkage_from_hours(0, pauses=1)


def test_scheduled_headcount_rounds_up():
    # 10 agents on the phones with 20% shrinkage -> 12.5 -> 13 people
    assert list(scheduled_headcount([10, 0, 4], 20)) == [13, 0, 5]
    assert list(scheduled_headcount([8], 0)) == [8]
    assert list(scheduled_headcount([9], 10)) == [10]  # exactly 10.0, no float noise upward
    assert list(scheduled_headcount([10, 10], [0, 50])) == [10, 20]
    with pytest.raises(ValueError):
        scheduled_headcount([1], 100)


def test_shrinkage_by_weekday_and_hour_with_default():
    index = pd.date_range("2024-03-04 08:00", periods=3, freq="h")  # Monday
    table = pd.DataFrame({"weekday": [0], "hour": [9], "shrinkage_pct": [40.0]})
    assert list(shrinkage_for_index(index, table, 20)) == [20, 40, 20]
    assert list(shrinkage_for_index(index, None, 15)) == [15, 15, 15]


def test_daily_summary():
    index = pd.date_range("2024-03-04 00:00", periods=4, freq="30min")
    plan = pd.DataFrame({"agents": [2, 4, 4, 2], "scheduled": [3, 5, 5, 3]}, index=index)
    out = daily_summary(plan, 30, shift_hours=8)
    row = out.iloc[0]
    assert row["agent_hours"] == pytest.approx(6.0)
    assert row["scheduled_hours"] == pytest.approx(8.0)
    assert row["peak_agents"] == 4
    assert row["fte"] == pytest.approx(1.0)
    assert np.isfinite(out.to_numpy()).all()
