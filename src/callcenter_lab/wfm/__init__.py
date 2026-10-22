"""Workforce management: from forecast calls to the agents and people a contact center needs."""

from .config import PRESET_LABELS, PRESETS, VALID_INTERVALS, StaffingConfig, preset
from .shrinkage import (
    ShrinkageConfig,
    daily_summary,
    scheduled_headcount,
    shrinkage_for_index,
    shrinkage_from_hours,
)

__all__ = [
    "PRESETS",
    "PRESET_LABELS",
    "VALID_INTERVALS",
    "ShrinkageConfig",
    "StaffingConfig",
    "daily_summary",
    "preset",
    "scheduled_headcount",
    "shrinkage_for_index",
    "shrinkage_from_hours",
]
