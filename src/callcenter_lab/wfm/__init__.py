"""Workforce management: from forecast calls to the agents and people a contact center needs."""

from .config import PRESET_LABELS, PRESETS, VALID_INTERVALS, StaffingConfig, preset
from .erlang import (
    asa,
    erlang_a,
    erlang_b,
    erlang_c,
    occupancy,
    required_agents,
    required_agents_erlang_a,
    service_level,
    size_staffing,
)
from .plan import build_plan, build_plan_range
from .shrinkage import (
    ShrinkageConfig,
    daily_summary,
    scheduled_headcount,
    shrinkage_for_index,
    shrinkage_from_hours,
)
from .workload import (
    ConstantAHT,
    ProfileAHT,
    SeriesAHT,
    forecast_aht,
    load_aht_csv,
    synthetic_aht,
    workload_erlangs,
)

__all__ = [
    "PRESETS",
    "PRESET_LABELS",
    "VALID_INTERVALS",
    "ConstantAHT",
    "ProfileAHT",
    "SeriesAHT",
    "ShrinkageConfig",
    "StaffingConfig",
    "asa",
    "build_plan",
    "build_plan_range",
    "daily_summary",
    "erlang_a",
    "erlang_b",
    "erlang_c",
    "forecast_aht",
    "load_aht_csv",
    "occupancy",
    "preset",
    "required_agents",
    "required_agents_erlang_a",
    "scheduled_headcount",
    "service_level",
    "shrinkage_for_index",
    "shrinkage_from_hours",
    "size_staffing",
    "synthetic_aht",
    "workload_erlangs",
]
