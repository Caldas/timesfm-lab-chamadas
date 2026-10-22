"""StaffingConfig: every parameter of the staffing calculation in one place."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from .shrinkage import ShrinkageConfig

VALID_INTERVALS = (5, 10, 15, 20, 30, 60)


@dataclass(frozen=True)
class StaffingConfig:
    """Parameters for turning forecast calls into agents.

    Defaults are examples to start from, not a reference for any real operation.
    """

    interval_minutes: int = 30
    service_level_pct: float = 80.0  # "X% of calls answered..."
    service_level_seconds: float = 20.0  # "...within Y seconds"
    max_occupancy_pct: float = 85.0  # cap on agent busy time
    max_asa_seconds: float | None = None  # optional cap on average speed of answer
    mean_patience_seconds: float | None = None  # None: callers never hang up (Erlang C)
    aht_seconds: float = 300.0  # average handling time used when no AHT profile is given
    shrinkage: ShrinkageConfig = field(default_factory=ShrinkageConfig)
    cost_per_hour: float | None = None  # cost of one scheduled person-hour (optional)
    shift_hours: float = 8.0  # paid hours per person per day, to turn hours into FTE

    def __post_init__(self) -> None:
        if self.interval_minutes not in VALID_INTERVALS:
            raise ValueError(
                f"interval_minutes deve ser um destes: {VALID_INTERVALS} (recebi {self.interval_minutes})."
            )
        if not 0 < self.service_level_pct <= 100:
            raise ValueError("service_level_pct deve estar entre 0 (exclusive) e 100.")
        if self.service_level_seconds < 0:
            raise ValueError("service_level_seconds não pode ser negativo.")
        if not 0 < self.max_occupancy_pct <= 100:
            raise ValueError("max_occupancy_pct deve estar entre 0 (exclusive) e 100.")
        if self.max_asa_seconds is not None and self.max_asa_seconds < 0:
            raise ValueError("max_asa_seconds não pode ser negativo.")
        if self.mean_patience_seconds is not None and self.mean_patience_seconds <= 0:
            raise ValueError("mean_patience_seconds deve ser maior que zero (ou None).")
        if self.aht_seconds <= 0:
            raise ValueError("aht_seconds deve ser maior que zero.")
        if self.cost_per_hour is not None and self.cost_per_hour < 0:
            raise ValueError("cost_per_hour não pode ser negativo.")
        if self.shift_hours <= 0:
            raise ValueError("shift_hours deve ser maior que zero.")

    @property
    def interval_seconds(self) -> int:
        return self.interval_minutes * 60

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> StaffingConfig:
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"Parâmetro(s) desconhecido(s): {sorted(unknown)}. Válidos: {sorted(known)}.")
        data = dict(data)
        if "shrinkage" in data:
            data["shrinkage"] = ShrinkageConfig(**data["shrinkage"])
        return cls(**data)

    def save(self, path: str | Path) -> None:
        """Write the configuration as JSON."""
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> StaffingConfig:
        """Read a configuration written by ``save``."""
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


# Examples to start from; edit freely. They are NOT a reference for any real operation.
PRESETS: dict[str, StaffingConfig] = {
    "80-20": StaffingConfig(service_level_pct=80, service_level_seconds=20),
    "90-30": StaffingConfig(service_level_pct=90, service_level_seconds=30, max_occupancy_pct=80),
}
PRESET_LABELS = {
    "80-20": "80% em 20 s (exemplo)",
    "90-30": "90% em 30 s, ocupação máx. 80% (exemplo)",
}


def preset(name: str) -> StaffingConfig:
    if name not in PRESETS:
        raise ValueError(f"Preset desconhecido: {name!r}. Opções: {sorted(PRESETS)}.")
    return PRESETS[name]
