"""Shrinkage: the share of paid time agents are NOT available to take calls.

Staffing math gives the agents needed *on the phones*. Breaks, training, absenteeism and vacation
mean more people must be scheduled than that: ``scheduled = agents / (1 - shrinkage)``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

COMPONENTS = ("pauses_pct", "training_pct", "absenteeism_pct", "vacation_pct", "other_pct")


@dataclass(frozen=True)
class ShrinkageConfig:
    """Shrinkage components, each as a percentage of paid time.

    The defaults are only an example, not a reference for any real operation.
    """

    pauses_pct: float = 10.0
    training_pct: float = 3.0
    absenteeism_pct: float = 5.0
    vacation_pct: float = 5.0
    other_pct: float = 2.0

    def __post_init__(self) -> None:
        for name in COMPONENTS:
            value = getattr(self, name)
            if not 0 <= value < 100:
                raise ValueError(f"{name} deve estar entre 0 e 100 (recebi {value}).")
        if self.total_pct >= 100:
            raise ValueError(f"A soma do shrinkage deve ser menor que 100% (é {self.total_pct}%).")

    @property
    def total_pct(self) -> float:
        """Sum of all components, in percent."""
        return float(sum(getattr(self, name) for name in COMPONENTS))

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


def shrinkage_from_hours(paid_hours: float, **hours: float) -> ShrinkageConfig:
    """Build a ShrinkageConfig from hours instead of percentages.

    ``hours`` uses the same names as the components without the ``_pct`` suffix, e.g.
    ``shrinkage_from_hours(160, pauses=16, training=4, absenteeism=8, vacation=8, other=2)``.
    """
    if paid_hours <= 0:
        raise ValueError("paid_hours deve ser maior que zero.")
    valid = {name.removesuffix("_pct") for name in COMPONENTS}
    unknown = set(hours) - valid
    if unknown:
        raise ValueError(f"Componente desconhecido: {sorted(unknown)}. Use: {sorted(valid)}.")
    return ShrinkageConfig(**{f"{name}_pct": value / paid_hours * 100 for name, value in hours.items()})


def scheduled_headcount(agents, shrinkage_pct):
    """People to schedule so that ``agents`` are available on the phones (rounded up).

    ``shrinkage_pct`` can be a single number or an array aligned with ``agents``.
    """
    agents = np.asarray(agents, dtype=float)
    shrink = np.asarray(shrinkage_pct, dtype=float)
    if np.any(shrink < 0) or np.any(shrink >= 100):
        raise ValueError("shrinkage_pct deve estar entre 0 e 100 (exclusive).")
    # round() first removes float noise such as 9.0000000001 before ceil
    return np.ceil(np.round(agents / (1 - shrink / 100), 9)).astype(int)


def shrinkage_for_index(index: pd.DatetimeIndex, table: pd.DataFrame | None, default_pct: float) -> np.ndarray:
    """Shrinkage per interval from an optional table of ``weekday`` (0=Mon), ``hour`` and ``shrinkage_pct``.

    Intervals not covered by the table use ``default_pct``.
    """
    if table is None or table.empty:
        return np.full(len(index), float(default_pct))
    lookup = {(int(r.weekday), int(r.hour)): float(r.shrinkage_pct) for r in table.itertuples()}
    return np.array(
        [lookup.get((int(day), int(hour)), float(default_pct)) for day, hour in zip(index.dayofweek, index.hour)]
    )


def daily_summary(plan: pd.DataFrame, interval_minutes: int, shift_hours: float = 8.0) -> pd.DataFrame:
    """Per day: agent-hours on the phones, scheduled hours, FTE and peak headcount.

    ``plan`` needs the columns ``agents`` and ``scheduled`` indexed by interval start.
    """
    if shift_hours <= 0:
        raise ValueError("shift_hours deve ser maior que zero.")
    hours = interval_minutes / 60
    day = plan.index.normalize()
    out = pd.DataFrame(
        {
            "agent_hours": (plan["agents"] * hours).groupby(day).sum(),
            "scheduled_hours": (plan["scheduled"] * hours).groupby(day).sum(),
            "peak_agents": plan["agents"].groupby(day).max(),
            "peak_scheduled": plan["scheduled"].groupby(day).max(),
        }
    )
    out["fte"] = out["scheduled_hours"] / shift_hours
    return out

