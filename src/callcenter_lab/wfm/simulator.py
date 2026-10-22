"""A small discrete-event simulator of a contact center (one queue, equal agents).

Calls arrive (Poisson, spread uniformly inside each interval), wait in a first-come-first-served
queue, are answered by one of the agents scheduled for that interval, and may hang up after an
exponentially distributed patience. Use it to check the Erlang formulas, to test a staffing plan or
a roster, and to produce synthetic call-center data with handling time, wait and abandonment.

Conventions (the same ones the Erlang module uses):
- Calls are counted in the interval where they *arrive*.
- ``service_level_pct`` = calls answered within the threshold / all calls offered.
- When the number of agents drops, agents already on a call finish it (no one is cut off).
- The simulation starts with an empty system, so the first intervals look better than reality;
  skip a few warm-up intervals when comparing with steady-state formulas.
"""

from __future__ import annotations

import heapq
import math
import warnings
from collections import deque
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import StaffingConfig
from .plan import build_plan

# event kinds, in the order they are handled when several happen at the same instant
_CAPACITY, _COMPLETION, _ABANDON = 0, 1, 2

# two-sided 95% Student-t critical values for 1..30 degrees of freedom
_T95 = [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228, 2.201, 2.179, 2.160, 2.145, 2.131,
        2.120, 2.110, 2.101, 2.093, 2.086, 2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042]

METRICS = (
    "offered", "answered", "abandoned", "service_level_pct", "abandon_pct",
    "avg_wait_answered_seconds", "avg_handle_seconds", "occupancy_pct",
)


@dataclass(frozen=True)
class SimulationResult:
    """Per-interval results (indexed by interval start) and, optionally, one row per call."""

    intervals: pd.DataFrame
    calls: pd.DataFrame | None = None


def _service_times(rng: np.random.Generator, means: np.ndarray, cv: float) -> np.ndarray:
    if cv <= 0:
        raise ValueError("aht_cv deve ser maior que zero.")
    if abs(cv - 1.0) < 1e-12:
        return rng.exponential(means)
    sigma2 = math.log(1 + cv**2)
    return rng.lognormal(np.log(means) - sigma2 / 2, math.sqrt(sigma2))


def simulate(
    calls_per_interval,
    agents_per_interval,
    aht_seconds,
    interval_minutes: int,
    *,
    mean_patience_seconds: float | None = None,
    service_level_seconds: float = 20.0,
    aht_cv: float = 1.0,
    seed: int = 0,
    index: pd.DatetimeIndex | None = None,
    record_calls: bool = False,
) -> SimulationResult:
    """Simulate the queue interval by interval.

    ``calls_per_interval`` is the *expected* number of calls (the actual number is Poisson).
    ``agents_per_interval`` and ``aht_seconds`` are arrays (or numbers) with one value per interval.
    ``aht_cv`` is the coefficient of variation of the handling time (1.0 = exponential).
    """
    calls = np.asarray(calls_per_interval, dtype=float)
    n_int = len(calls)
    if n_int == 0:
        raise ValueError("Preciso de pelo menos um intervalo.")
    if np.any(calls < 0):
        raise ValueError("O número de chamadas não pode ser negativo.")
    agents = np.broadcast_to(np.asarray(agents_per_interval, dtype=int), calls.shape)
    aht = np.broadcast_to(np.asarray(aht_seconds, dtype=float), calls.shape)
    if np.any(agents < 0) or np.any(aht <= 0):
        raise ValueError("agents não pode ser negativo e aht_seconds deve ser maior que zero.")
    if mean_patience_seconds is not None and mean_patience_seconds <= 0:
        raise ValueError("mean_patience_seconds deve ser maior que zero (ou None).")
    length = interval_minutes * 60.0
    rng = np.random.default_rng(seed)

    # --- arrivals -----------------------------------------------------------------------------
    counts = rng.poisson(calls)
    arr_int = np.repeat(np.arange(n_int), counts)
    arr_time = np.sort(arr_int * length + rng.uniform(0, length, size=arr_int.size)) if arr_int.size else np.empty(0)
    arr_int = np.minimum((arr_time // length).astype(int), n_int - 1)
    n_calls = arr_time.size
    service = _service_times(rng, aht[arr_int], aht_cv) if n_calls else np.empty(0)
    patience = (
        rng.exponential(mean_patience_seconds, size=n_calls) if mean_patience_seconds is not None else np.full(n_calls, np.inf)
    )

    # --- event loop ---------------------------------------------------------------------------
    wait = np.full(n_calls, np.nan)  # wait until answered or until hanging up
    answered = np.zeros(n_calls, dtype=bool)
    abandoned = np.zeros(n_calls, dtype=bool)
    start = np.full(n_calls, np.nan)
    waiting = np.zeros(n_calls, dtype=bool)
    queue: deque[int] = deque()
    heap: list[tuple[float, int, int]] = [(i * length, _CAPACITY, i) for i in range(1, n_int)]
    heapq.heapify(heap)
    busy, capacity, nxt = 0, int(agents[0]), 0

    def start_waiting(now: float) -> None:
        nonlocal busy
        while busy < capacity and queue:
            c = queue.popleft()
            if not waiting[c]:
                continue  # already hung up
            waiting[c] = False
            answered[c] = True
            wait[c] = now - arr_time[c]
            start[c] = now
            busy += 1
            heapq.heappush(heap, (now + service[c], _COMPLETION, c))

    while nxt < n_calls or heap:
        if nxt < n_calls and (not heap or arr_time[nxt] < heap[0][0]):
            now, c = arr_time[nxt], nxt
            nxt += 1
            waiting[c] = True
            queue.append(c)
            if np.isfinite(patience[c]):
                heapq.heappush(heap, (now + patience[c], _ABANDON, c))
            start_waiting(now)
            continue
        now, kind, ref = heapq.heappop(heap)
        if kind == _CAPACITY:
            capacity = int(agents[ref])
            start_waiting(now)
        elif kind == _COMPLETION:
            busy -= 1
            start_waiting(now)
        elif waiting[ref]:  # _ABANDON of a call that is still waiting
            waiting[ref] = False
            abandoned[ref] = True
            wait[ref] = now - arr_time[ref]

    # --- metrics per interval -----------------------------------------------------------------
    def per_interval(mask: np.ndarray) -> np.ndarray:
        return np.bincount(arr_int[mask], minlength=n_int) if n_calls else np.zeros(n_int, dtype=int)

    offered = per_interval(np.ones(n_calls, dtype=bool))
    n_answered = per_interval(answered)
    n_abandoned = per_interval(abandoned)
    within = per_interval(answered & (np.nan_to_num(wait, nan=np.inf) <= service_level_seconds))

    def mean_by_interval(values: np.ndarray, mask: np.ndarray) -> np.ndarray:
        if not n_calls:
            return np.full(n_int, np.nan)
        total = np.bincount(arr_int[mask], weights=values[mask], minlength=n_int)
        count = np.bincount(arr_int[mask], minlength=n_int)
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(count > 0, total / count, np.nan)

    # busy agent-time inside each interval: F(t) = total busy time up to t, evaluated at the boundaries
    boundaries = np.arange(n_int + 1) * length
    busy_start = start[answered]
    cumulative = np.array([np.clip(b - busy_start, 0, service[answered]).sum() for b in boundaries])
    busy_time = np.diff(cumulative)
    capacity_time = agents * length
    with np.errstate(invalid="ignore", divide="ignore"):
        occupancy = np.where(capacity_time > 0, 100 * busy_time / capacity_time, np.nan)
        service_level = np.where(offered > 0, 100 * within / offered, np.nan)
        abandon_pct = np.where(offered > 0, 100 * n_abandoned / offered, np.nan)

    result = pd.DataFrame(
        {
            "offered": offered,
            "answered": n_answered,
            "abandoned": n_abandoned,
            "service_level_pct": service_level,
            "abandon_pct": abandon_pct,
            "avg_wait_answered_seconds": mean_by_interval(wait, answered),
            "avg_handle_seconds": mean_by_interval(service, answered),
            "occupancy_pct": occupancy,
            "agents": agents,
        },
        index=index if index is not None else pd.RangeIndex(n_int),
    )
    per_call = None
    if record_calls:
        per_call = pd.DataFrame(
            {"arrival_seconds": arr_time, "interval": arr_int, "wait_seconds": wait,
             "handle_seconds": np.where(answered, service, np.nan), "answered": answered, "abandoned": abandoned}
        )
    return SimulationResult(result, per_call)


# --- Replications and confidence intervals ----------------------------------------------------
def _half_width(values: np.ndarray) -> float:
    values = values[~np.isnan(values)]
    n = len(values)
    if n < 2:
        return float("nan")
    t = _T95[n - 2] if n - 1 <= len(_T95) else 1.96
    return float(t * values.std(ddof=1) / math.sqrt(n))


def overall_metrics(intervals: pd.DataFrame, skip: int = 0) -> dict[str, float]:
    """Whole-run figures from the per-interval table, weighting each interval by its calls."""
    data = intervals.iloc[skip:]
    offered = data["offered"].sum()
    answered = data["answered"].sum()
    if offered == 0:
        return {name: float("nan") for name in ("service_level_pct", "abandon_pct", "avg_wait_answered_seconds", "occupancy_pct")}
    within = (data["service_level_pct"].fillna(0) / 100 * data["offered"]).sum()
    wait = (data["avg_wait_answered_seconds"].fillna(0) * data["answered"]).sum() / answered if answered else float("nan")
    capacity_time = data["agents"].sum()
    occ = (data["occupancy_pct"].fillna(0) * data["agents"]).sum() / capacity_time if capacity_time else float("nan")
    return {
        "service_level_pct": float(100 * within / offered),
        "abandon_pct": float(100 * data["abandoned"].sum() / offered),
        "avg_wait_answered_seconds": float(wait),
        "occupancy_pct": float(occ),
    }


@dataclass(frozen=True)
class ReplicationResult:
    """Mean over replications with a 95% confidence half-width, per interval and overall."""

    intervals: pd.DataFrame  # for each metric: <metric> (mean) and <metric>_ci (half-width)
    overall: dict[str, tuple[float, float]]  # metric -> (mean, half-width)
    n_replications: int


def simulate_replications(
    calls_per_interval, agents_per_interval, aht_seconds, interval_minutes: int,
    *, n_replications: int = 10, seed: int = 0, warmup_intervals: int = 0, **kwargs,
) -> ReplicationResult:
    """Run the simulation several times (seeds ``seed``, ``seed+1``, ...) and summarise."""
    if n_replications < 1:
        raise ValueError("n_replications deve ser pelo menos 1.")
    runs = [
        simulate(calls_per_interval, agents_per_interval, aht_seconds, interval_minutes, seed=seed + r, **kwargs).intervals
        for r in range(n_replications)
    ]
    stacked = {name: np.stack([run[name].to_numpy(dtype=float) for run in runs]) for name in METRICS}
    out = pd.DataFrame(index=runs[0].index)
    for name, values in stacked.items():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)  # intervals with no calls are all-NaN
            out[name] = np.nanmean(values, axis=0)
        out[f"{name}_ci"] = [_half_width(values[:, i]) for i in range(values.shape[1])]
    out["agents"] = runs[0]["agents"]
    per_run = [overall_metrics(run, warmup_intervals) for run in runs]
    overall = {
        name: (float(np.nanmean([m[name] for m in per_run])), _half_width(np.array([m[name] for m in per_run])))
        for name in per_run[0]
    }
    return ReplicationResult(out, overall, n_replications)


# --- Synthetic call-center data ---------------------------------------------------------------
def generate_dataset(
    calls: pd.Series, config: StaffingConfig, aht=None, agents=None, seed: int = 0, aht_cv: float = 1.0
) -> pd.DataFrame:
    """Simulate one run and return the data a real ACD report would give, per interval.

    ``calls`` is the expected calls per interval (indexed by interval start). If ``agents`` is not
    given, the staffing plan for the configuration is used. Columns: ``timestamp``,
    ``calls_offered``, ``calls_answered``, ``calls_abandoned``, ``aht_seconds``,
    ``avg_wait_seconds``, ``service_level_pct``, plus ``agents`` and ``occupancy_pct``.
    """
    plan = build_plan(calls, config, aht)
    agent_counts = plan["agents"].to_numpy() if agents is None else np.asarray(agents)
    run = simulate(
        calls.to_numpy(dtype=float), agent_counts, plan["aht_seconds"].to_numpy(), config.interval_minutes,
        mean_patience_seconds=config.mean_patience_seconds, service_level_seconds=config.service_level_seconds,
        aht_cv=aht_cv, seed=seed, index=calls.index,
    ).intervals
    return pd.DataFrame(
        {
            "timestamp": calls.index,
            "calls_offered": run["offered"].to_numpy(),
            "calls_answered": run["answered"].to_numpy(),
            "calls_abandoned": run["abandoned"].to_numpy(),
            "aht_seconds": run["avg_handle_seconds"].to_numpy(),
            "avg_wait_seconds": run["avg_wait_answered_seconds"].to_numpy(),
            "service_level_pct": run["service_level_pct"].to_numpy(),
            "agents": run["agents"].to_numpy(),
            "occupancy_pct": run["occupancy_pct"].to_numpy(),
        }
    )
