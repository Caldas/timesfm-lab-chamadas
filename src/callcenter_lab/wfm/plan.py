"""The full chain: calls per interval -> workload -> agents -> people to schedule (-> cost)."""

from __future__ import annotations

import pandas as pd

from .config import StaffingConfig
from .erlang import size_staffing
from .workload import ConstantAHT, workload_erlangs


def _check_interval(index: pd.DatetimeIndex, config: StaffingConfig) -> None:
    if len(index) > 1:
        step = (index[1] - index[0]).total_seconds() / 60
        if abs(step - config.interval_minutes) > 1e-9:
            raise ValueError(
                f"O intervalo da série ({step:g} min) é diferente do configurado "
                f"({config.interval_minutes} min). Ajuste um dos dois."
            )


def build_plan(calls: pd.Series, config: StaffingConfig, aht=None) -> pd.DataFrame:
    """Staffing plan for calls per interval (a series indexed by interval start).

    ``aht`` is any object with ``for_index(index)`` (see ``workload``); by default the constant
    ``config.aht_seconds``. Columns: calls, aht_seconds, workload_erlangs, agents, service_level_pct,
    asa_seconds, occupancy_pct, prob_wait, abandon_pct, scheduled and, if a cost is configured, cost.
    """
    if not isinstance(calls.index, pd.DatetimeIndex):
        raise TypeError("A série de chamadas precisa ter um índice de data/hora.")
    _check_interval(calls.index, config)
    aht_model = aht if aht is not None else ConstantAHT(config.aht_seconds)
    aht_seconds = aht_model.for_index(calls.index)
    volume = calls.clip(lower=0).to_numpy(dtype=float)
    loads = workload_erlangs(volume, aht_seconds, config.interval_minutes)

    sized = size_staffing(loads, aht_seconds, config, calls.index)
    plan = pd.DataFrame(index=calls.index)
    plan["calls"] = volume
    plan["aht_seconds"] = aht_seconds
    plan["workload_erlangs"] = loads
    plan = plan.join(sized)
    if config.cost_per_hour is not None:
        plan["cost"] = plan["scheduled"] * (config.interval_minutes / 60) * config.cost_per_hour
    return plan


def build_plan_range(
    point: pd.Series, lower: pd.Series, upper: pd.Series, config: StaffingConfig, aht=None
) -> pd.DataFrame:
    """Agents and scheduled people for the 10% (low), median (expected) and 90% (high) volume forecasts."""
    out = pd.DataFrame(index=point.index)
    for label, series in (("low", lower), ("expected", point), ("high", upper)):
        plan = build_plan(series, config, aht)
        out[f"calls_{label}"] = plan["calls"]
        out[f"agents_{label}"] = plan["agents"]
        out[f"scheduled_{label}"] = plan["scheduled"]
    return out
