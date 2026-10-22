"""Several queues: size each queue on its own (the default), or compare separate teams with a cross-trained one.

Sizing each queue independently applies the Erlang model to every queue and adds the results. It is exactly
right when each queue has its own agents who cannot answer the others. When agents can answer several queues
(cross-trained), the calls of all queues share the same team, which needs fewer agents for the same service
level (the "pooling" effect); how many fewer is what ``compare_pooling`` measures with the skills simulator.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import StaffingConfig
from .erlang import size_staffing
from .plan import build_plan
from .skills import (
    AgentGroup,
    QueueSpec,
    SkillsReplications,
    simulate_skills_replications,
)
from .workload import ConstantAHT


def queue_config(config: StaffingConfig, aht_seconds: float) -> StaffingConfig:
    """The base configuration with the AHT of one queue."""
    return dataclasses.replace(config, aht_seconds=float(aht_seconds))


def _aht_of(aht_by_queue: Mapping[str, float] | None, name: str, config: StaffingConfig) -> float:
    return float((aht_by_queue or {}).get(name, config.aht_seconds))


@dataclass(frozen=True)
class QueuePlans:
    """The staffing plan of each queue and their sum."""

    plans: dict[str, pd.DataFrame]
    total: pd.DataFrame  # per interval: calls, agents, scheduled and the agents of each queue
    interval_minutes: int

    def summary(self) -> pd.DataFrame:
        """One row per queue plus a "Total" row: calls, peak agents, agent hours and scheduled hours."""
        hours = self.interval_minutes / 60
        rows = {
            name: {
                "calls": plan["calls"].sum(), "peak_agents": plan["agents"].max(), "agent_hours": plan["agents"].sum() * hours,
                "peak_scheduled": plan["scheduled"].max(), "scheduled_hours": plan["scheduled"].sum() * hours,
            }
            for name, plan in self.plans.items()
        }
        rows["Total"] = {
            "calls": self.total["calls"].sum(), "peak_agents": self.total["agents"].max(),
            "agent_hours": self.total["agents"].sum() * hours, "peak_scheduled": self.total["scheduled"].max(),
            "scheduled_hours": self.total["scheduled"].sum() * hours,
        }
        return pd.DataFrame(rows).T


def build_queue_plans(
    calls_by_queue: Mapping[str, pd.Series], config: StaffingConfig, aht_by_queue: Mapping[str, float] | None = None
) -> QueuePlans:
    """Size every queue independently. ``aht_by_queue`` maps a queue to its AHT in seconds (default: ``config``)."""
    if not calls_by_queue:
        raise ValueError("Informe pelo menos uma fila.")
    plans = {
        name: build_plan(calls, config, ConstantAHT(_aht_of(aht_by_queue, name, config)))
        for name, calls in calls_by_queue.items()
    }
    first = next(iter(plans.values()))
    total = pd.DataFrame(index=first.index)
    total["calls"] = sum(p["calls"] for p in plans.values())
    total["agents"] = sum(p["agents"] for p in plans.values())
    total["scheduled"] = sum(p["scheduled"] for p in plans.values())
    for name, plan in plans.items():
        total[f"agents_{name}"] = plan["agents"]
    return QueuePlans(plans, total, config.interval_minutes)


def pooled_plan(
    calls_by_queue: Mapping[str, pd.Series], config: StaffingConfig, aht_by_queue: Mapping[str, float] | None = None
) -> pd.DataFrame:
    """Size one cross-trained team that answers every queue: the workloads add up and the AHT is their weighted mean."""
    names = list(calls_by_queue)
    index = calls_by_queue[names[0]].index
    seconds = config.interval_seconds
    load = sum(calls_by_queue[n].clip(lower=0).to_numpy(dtype=float) * _aht_of(aht_by_queue, n, config) / seconds for n in names)
    calls = sum(calls_by_queue[n].clip(lower=0).to_numpy(dtype=float) for n in names)
    with np.errstate(invalid="ignore", divide="ignore"):
        aht = np.where(calls > 0, load * seconds / calls, config.aht_seconds)
    plan = size_staffing(load, aht, config, index)
    plan.insert(0, "calls", calls)
    plan.insert(1, "workload_erlangs", load)
    return plan


@dataclass(frozen=True)
class PoolingComparison:
    summary: pd.DataFrame  # one row per design
    per_queue: pd.DataFrame  # one row per design and queue: simulated service level, abandonment, wait
    agents: pd.DataFrame  # agents per interval in each design
    separate: SkillsReplications
    pooled: SkillsReplications


def compare_pooling(
    calls_by_queue: Mapping[str, pd.Series],
    config: StaffingConfig,
    aht_by_queue: Mapping[str, float] | None = None,
    *,
    n_replications: int = 10,
    seed: int = 0,
    routing: str = "longest_wait",
    warmup_intervals: int = 0,
) -> PoolingComparison:
    """Separate teams (one per queue) against one cross-trained team, both sized for the same goal and simulated.

    Separate: each queue is sized with Erlang on its own and has its own specialists. Cross-trained: one team
    sized on the summed workload, who can answer every queue. The simulator reports what each design delivers.
    """
    separate_plans = build_queue_plans(calls_by_queue, config, aht_by_queue)
    pooled = pooled_plan(calls_by_queue, config, aht_by_queue)
    names = list(calls_by_queue)
    expected = {n: calls_by_queue[n].clip(lower=0).to_numpy(dtype=float) for n in names}
    specs = [
        QueueSpec(n, _aht_of(aht_by_queue, n, config), config.mean_patience_seconds, config.service_level_seconds)
        for n in names
    ]
    run_args = {"n_replications": n_replications, "seed": seed, "warmup_intervals": warmup_intervals, "routing": routing}
    separate_groups = [AgentGroup(f"Especialistas {n}", (n,), separate_plans.plans[n]["agents"].to_numpy()) for n in names]
    pooled_groups = [AgentGroup("Equipe cruzada", tuple(names), pooled["agents"].to_numpy())]
    separate_result = simulate_skills_replications(expected, separate_groups, specs, config.interval_minutes, **run_args)
    pooled_result = simulate_skills_replications(expected, pooled_groups, specs, config.interval_minutes, **run_args)

    hours = config.interval_minutes / 60
    agents = pd.DataFrame({"Equipes separadas": separate_plans.total["agents"], "Equipe cruzada": pooled["agents"]})
    scheduled = {"Equipes separadas": separate_plans.total["scheduled"], "Equipe cruzada": pooled["scheduled"]}
    summary_rows, queue_rows = {}, []
    for design, result in (("Equipes separadas", separate_result), ("Equipe cruzada", pooled_result)):
        levels = [result.queues[n]["service_level_pct"][0] for n in names]
        summary_rows[design] = {
            "peak_agents": float(agents[design].max()),
            "agent_hours": float(agents[design].sum() * hours),
            "scheduled_hours": float(scheduled[design].sum() * hours),
            "min_service_level_pct": float(np.nanmin(levels)),
            "avg_service_level_pct": float(np.nanmean(levels)),
            "avg_abandon_pct": float(np.nanmean([result.queues[n]["abandon_pct"][0] for n in names])),
        }
        for n in names:
            queue_rows.append({
                "design": design, "queue": n,
                "service_level_pct": result.queues[n]["service_level_pct"][0],
                "service_level_ci": result.queues[n]["service_level_pct"][1],
                "abandon_pct": result.queues[n]["abandon_pct"][0],
                "avg_wait_answered_seconds": result.queues[n]["avg_wait_answered_seconds"][0],
            })
    summary = pd.DataFrame(summary_rows).T
    base = summary.loc["Equipes separadas", "agent_hours"]
    summary["agent_hours_vs_separate_pct"] = 100 * (summary["agent_hours"] - base) / base if base else np.nan
    return PoolingComparison(summary, pd.DataFrame(queue_rows), agents, separate_result, pooled_result)
