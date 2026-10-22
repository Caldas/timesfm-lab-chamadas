""""What if" scenarios: re-run the staffing plan with different volume, AHT, shrinkage or goals and compare.

A scenario changes the base ``StaffingConfig`` and/or the inputs (volume from the 10%/50%/90% forecast,
multipliers for volume and AHT). ``run_scenarios`` puts them side by side; ``sensitivity`` varies one
parameter at a time. If a roster is given, each scenario also shows how that fixed roster would cope.
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd

from .config import StaffingConfig
from .plan import build_plan
from .scheduling import Roster
from .shrinkage import ShrinkageConfig, daily_summary
from .workload import ConstantAHT, ScaledAHT

VOLUMES = ("low", "expected", "high")
VOLUME_LABELS = {"low": "baixo", "expected": "esperado", "high": "alto"}


@dataclass(frozen=True)
class Scenario:
    """Changes to apply to the base case. Anything left as ``None`` / neutral keeps the base value."""

    name: str
    volume: str = "expected"  # which forecast to use: low (10%), expected (median) or high (90%)
    volume_factor: float = 1.0  # multiplies the calls
    aht_factor: float = 1.0  # multiplies the AHT
    shrinkage_pp: float = 0.0  # percentage points added to the total shrinkage
    service_level_pct: float | None = None
    service_level_seconds: float | None = None
    max_occupancy_pct: float | None = None
    mean_patience_seconds: float | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("O cenário precisa de um nome.")
        if self.volume not in VOLUMES:
            raise ValueError(f"volume deve ser um destes: {VOLUMES} (recebi {self.volume!r}).")
        if self.volume_factor <= 0 or self.aht_factor <= 0:
            raise ValueError("Os fatores de volume e de TMA devem ser maiores que zero.")


def adjust_shrinkage(shrinkage: ShrinkageConfig, delta_pp: float) -> ShrinkageConfig:
    """Add ``delta_pp`` percentage points to the total, scaling every component in proportion."""
    total = shrinkage.total_pct
    new_total = total + delta_pp
    if new_total < 0 or new_total >= 100:
        raise ValueError(f"O shrinkage total ficaria em {new_total:g}%: precisa estar entre 0 e 100.")
    if delta_pp == 0:
        return shrinkage
    if total == 0:
        return ShrinkageConfig(0, 0, 0, 0, new_total)
    factor = new_total / total
    return ShrinkageConfig(**{key: value * factor for key, value in shrinkage.to_dict().items()})


def apply_scenario(scenario: Scenario, config: StaffingConfig) -> StaffingConfig:
    """The configuration of a scenario: the base with its overrides."""
    overrides = {
        key: value
        for key, value in (
            ("service_level_pct", scenario.service_level_pct),
            ("service_level_seconds", scenario.service_level_seconds),
            ("max_occupancy_pct", scenario.max_occupancy_pct),
            ("mean_patience_seconds", scenario.mean_patience_seconds),
        )
        if value is not None
    }
    return dataclasses.replace(config, shrinkage=adjust_shrinkage(config.shrinkage, scenario.shrinkage_pp), **overrides)


def example_scenarios() -> list[Scenario]:
    """Common questions, as examples to edit."""
    return [
        Scenario("Base"),
        Scenario("Volume alto (90%)", volume="high"),
        Scenario("Volume baixo (10%)", volume="low"),
        Scenario("Volume +10%", volume_factor=1.1),
        Scenario("TMA +10%", aht_factor=1.1),
        Scenario("Absenteísmo +5 pontos", shrinkage_pp=5),
        Scenario("Meta 90% em 20 s", service_level_pct=90),
    ]


def _scenario_plan(volumes: Mapping[str, pd.Series], scenario: Scenario, config: StaffingConfig, aht) -> pd.DataFrame:
    if scenario.volume not in volumes:
        raise ValueError(
            f"O cenário '{scenario.name}' usa o volume {VOLUME_LABELS[scenario.volume]}, "
            "que só existe com a previsão do TimesFM."
        )
    base_aht = aht if aht is not None else ConstantAHT(config.aht_seconds)
    scenario_aht = ScaledAHT(base_aht, scenario.aht_factor) if scenario.aht_factor != 1 else base_aht
    return build_plan(volumes[scenario.volume] * scenario.volume_factor, apply_scenario(scenario, config), scenario_aht)


def _summarise(plan: pd.DataFrame, config: StaffingConfig) -> dict[str, float]:
    daily = daily_summary(plan, config.interval_minutes, config.shift_hours)
    calls = plan["calls"].sum()
    return {
        "calls_total": float(calls),
        "peak_agents": float(plan["agents"].max()),
        "agent_hours": float(daily["agent_hours"].sum()),
        "peak_scheduled": float(plan["scheduled"].max()),
        "scheduled_hours": float(daily["scheduled_hours"].sum()),
        "fte": float(daily["fte"].sum()),
        "expected_service_level_pct": float((plan["service_level_pct"] * plan["calls"]).sum() / calls) if calls else math.nan,
        "cost": float(plan["cost"].sum()) if "cost" in plan else math.nan,
    }


def run_scenarios(
    volumes: Mapping[str, pd.Series], scenarios: list[Scenario], config: StaffingConfig, aht=None, roster: Roster | None = None
) -> pd.DataFrame:
    """One row per scenario. The first scenario is the reference for the ``delta_*`` columns.

    ``volumes`` maps ``"low"``, ``"expected"`` and/or ``"high"`` to calls per interval. With a ``roster``,
    ``roster_shortfall_*`` and ``roster_surplus_*`` show how that fixed roster covers each scenario's need.
    """
    if not scenarios:
        raise ValueError("Informe pelo menos um cenário.")
    rows = []
    for scenario in scenarios:
        scenario_config = apply_scenario(scenario, config)
        plan = _scenario_plan(volumes, scenario, config, aht)
        row = {"scenario": scenario.name, "volume": VOLUME_LABELS[scenario.volume], **_summarise(plan, scenario_config)}
        if roster is not None:
            covered = roster.coverage["covered"].reindex(plan.index).fillna(0)
            gap = plan["scheduled"] - covered
            hours = scenario_config.interval_minutes / 60
            row["roster_shortfall_intervals"] = int((gap > 0).sum())
            row["roster_shortfall_person_hours"] = float(gap.clip(lower=0).sum() * hours)
            row["roster_surplus_person_hours"] = float((-gap).clip(lower=0).sum() * hours)
        rows.append(row)
    table = pd.DataFrame(rows)
    base = table.iloc[0]
    table["delta_agent_hours"] = table["agent_hours"] - base["agent_hours"]
    table["delta_agent_hours_pct"] = 100 * table["delta_agent_hours"] / base["agent_hours"] if base["agent_hours"] else math.nan
    table["delta_cost"] = table["cost"] - base["cost"]
    return table


SENSITIVITY_PARAMETERS = {
    "shrinkage_pp": ("Shrinkage (pontos percentuais a mais ou a menos)", (-5.0, -2.5, 0.0, 2.5, 5.0)),
    "aht_factor": ("TMA (multiplicador)", (0.9, 0.95, 1.0, 1.05, 1.1)),
    "volume_factor": ("Volume de chamadas (multiplicador)", (0.8, 0.9, 1.0, 1.1, 1.2)),
    "service_level_pct": ("Meta de nível de serviço (%)", (70.0, 80.0, 90.0, 95.0)),
    "max_occupancy_pct": ("Ocupação máxima (%)", (75.0, 80.0, 85.0, 90.0)),
}


def sensitivity(
    calls: pd.Series, config: StaffingConfig, parameter: str, values=None, aht=None
) -> pd.DataFrame:
    """Vary one parameter at a time over ``calls`` (the expected volume) and show the effect.

    ``parameter`` is a key of ``SENSITIVITY_PARAMETERS``. Columns: the value, peak agents, agent hours,
    scheduled hours, FTE, cost, and the change of agent hours against the base configuration.
    """
    if parameter not in SENSITIVITY_PARAMETERS:
        raise ValueError(f"Parâmetro desconhecido: {parameter!r}. Opções: {sorted(SENSITIVITY_PARAMETERS)}.")
    values = SENSITIVITY_PARAMETERS[parameter][1] if values is None else tuple(values)
    volumes = {"expected": calls}
    base = _summarise(_scenario_plan(volumes, Scenario("base"), config, aht), config)
    rows = []
    for value in values:
        scenario = Scenario("sensibilidade", **{parameter: value})
        scenario_config = apply_scenario(scenario, config)
        summary = _summarise(_scenario_plan(volumes, scenario, config, aht), scenario_config)
        rows.append({
            "value": value, "peak_agents": summary["peak_agents"], "agent_hours": summary["agent_hours"],
            "scheduled_hours": summary["scheduled_hours"], "fte": summary["fte"], "cost": summary["cost"],
            "delta_agent_hours_pct": 100 * (summary["agent_hours"] - base["agent_hours"]) / base["agent_hours"]
            if base["agent_hours"] else math.nan,
        })
    return pd.DataFrame(rows)


# --- scenarios as tables (for the interface) --------------------------------------------------------
SCENARIO_COLUMNS = ["nome", "volume", "fator_volume", "fator_TMA", "shrinkage_pp", "nível_serviço_%", "segundos",
                    "ocupação_máx_%", "paciência_s"]
_VOLUME_FROM_LABEL = {label: key for key, label in VOLUME_LABELS.items()}


def scenarios_to_table(scenarios: list[Scenario]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "nome": s.name, "volume": VOLUME_LABELS[s.volume], "fator_volume": s.volume_factor,
                "fator_TMA": s.aht_factor, "shrinkage_pp": s.shrinkage_pp, "nível_serviço_%": s.service_level_pct,
                "segundos": s.service_level_seconds, "ocupação_máx_%": s.max_occupancy_pct, "paciência_s": s.mean_patience_seconds,
            }
            for s in scenarios
        ],
        columns=SCENARIO_COLUMNS,
    )


def scenarios_from_table(table: pd.DataFrame) -> list[Scenario]:
    """Read scenarios from a table; blank cells keep the base value. Rows without a name are skipped."""
    def number(row, column, default):
        item = row.get(column)
        return default if item is None or (isinstance(item, float) and math.isnan(item)) or item == "" else float(item)

    scenarios = []
    for _, row in table.iterrows():
        name = row.get("nome")
        if name is None or (isinstance(name, float) and math.isnan(name)) or not str(name).strip():
            continue
        label = str(row.get("volume") or "esperado").strip().lower()
        if label not in _VOLUME_FROM_LABEL:
            raise ValueError(f"Volume inválido em '{name}': use baixo, esperado ou alto (recebi {label!r}).")
        scenarios.append(
            Scenario(
                name=str(name).strip(), volume=_VOLUME_FROM_LABEL[label],
                volume_factor=number(row, "fator_volume", 1.0), aht_factor=number(row, "fator_TMA", 1.0),
                shrinkage_pp=number(row, "shrinkage_pp", 0.0), service_level_pct=number(row, "nível_serviço_%", None),
                service_level_seconds=number(row, "segundos", None), max_occupancy_pct=number(row, "ocupação_máx_%", None),
                mean_patience_seconds=number(row, "paciência_s", None),
            )
        )
    if not scenarios:
        raise ValueError("Informe pelo menos um cenário.")
    return scenarios
