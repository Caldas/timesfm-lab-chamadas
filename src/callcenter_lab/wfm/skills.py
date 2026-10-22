"""Several queues and agents with skills: a discrete-event simulator with routing.

Erlang C assumes one queue and agents who can answer anything. With several queues and agents who only
handle some of them, no simple formula is right, so this module simulates the center:

- every queue has its own calls, average handling time (AHT), patience and service-level threshold;
- agents belong to *groups* (for example "specialists in sales" or "generalists") that list the queues they can
  answer and how many agents they have in each interval;
- a new call goes to a free agent that can serve its queue (``prefer`` decides which kind of agent first);
- when an agent becomes free, ``routing`` decides which waiting call it takes among the queues it can serve:
  the one waiting the longest, or by queue priority.

Conventions are the same as in ``simulator``: calls count in the interval where they arrive, the service level
is answered within the threshold divided by calls offered, agents already on a call finish it when the team
shrinks, and the simulation starts empty.
"""

from __future__ import annotations

import heapq
import math
import warnings
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .simulator import _half_width, _service_times

_CAPACITY, _COMPLETION, _ABANDON = 0, 1, 2
ROUTINGS = ("longest_wait", "priority")
PREFERENCES = ("specialist", "generalist")
QUEUE_METRICS = ("service_level_pct", "abandon_pct", "avg_wait_answered_seconds")


@dataclass(frozen=True)
class QueueSpec:
    """A queue: how long calls last, how patient callers are and the service-level goal threshold."""

    name: str
    aht_seconds: float = 300.0
    mean_patience_seconds: float | None = None
    service_level_seconds: float = 20.0
    priority: int = 0  # with routing="priority", lower numbers are served first

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("A fila precisa de um nome.")
        if self.aht_seconds <= 0:
            raise ValueError(f"O TMA da fila '{self.name}' deve ser maior que zero.")
        if self.mean_patience_seconds is not None and self.mean_patience_seconds <= 0:
            raise ValueError(f"A paciência da fila '{self.name}' deve ser maior que zero (ou None).")
        if self.service_level_seconds < 0:
            raise ValueError(f"O limite de nível de serviço da fila '{self.name}' não pode ser negativo.")


@dataclass(frozen=True)
class AgentGroup:
    """Agents who can answer a set of queues. ``agents`` is a number or one number per interval."""

    name: str
    skills: tuple[str, ...]
    agents: object

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("O grupo de agentes precisa de um nome.")
        if not self.skills:
            raise ValueError(f"O grupo '{self.name}' precisa atender pelo menos uma fila.")
        if np.any(np.asarray(self.agents) < 0):
            raise ValueError(f"O grupo '{self.name}' não pode ter agentes negativos.")


@dataclass(frozen=True)
class SkillsResult:
    queues: dict[str, pd.DataFrame]  # per queue, per interval: offered, answered, abandoned, service_level_pct...
    agents: pd.DataFrame  # agents per group per interval
    occupancy_pct: pd.DataFrame  # occupancy per group per interval


def simulate_skills(
    calls: Mapping[str, Sequence[float]],
    groups: Sequence[AgentGroup],
    queues: Sequence[QueueSpec],
    interval_minutes: int,
    *,
    routing: str = "longest_wait",
    prefer: str = "specialist",
    aht_cv: float = 1.0,
    seed: int = 0,
    index: pd.DatetimeIndex | None = None,
) -> SkillsResult:
    """Simulate the queues with skill-based routing, interval by interval.

    ``calls`` maps each queue name to the *expected* calls per interval (the real number is Poisson).
    """
    if routing not in ROUTINGS or prefer not in PREFERENCES:
        raise ValueError(f"routing deve ser um de {ROUTINGS} e prefer um de {PREFERENCES}.")
    specs = {q.name: q for q in queues}
    names = list(specs)
    if len(specs) != len(queues) or not names:
        raise ValueError("Informe filas com nomes diferentes (pelo menos uma).")
    if set(calls) != set(names):
        raise ValueError("As chamadas precisam ter exatamente as mesmas filas da lista de filas.")
    if not groups:
        raise ValueError("Informe pelo menos um grupo de agentes.")
    for group in groups:
        unknown = set(group.skills) - set(names)
        if unknown:
            raise ValueError(f"O grupo '{group.name}' atende filas que não existem: {sorted(unknown)}.")

    expected = {q: np.asarray(calls[q], dtype=float) for q in names}
    n_int = len(expected[names[0]])
    if n_int == 0 or any(len(v) != n_int for v in expected.values()) or any(np.any(v < 0) for v in expected.values()):
        raise ValueError("As chamadas precisam ter o mesmo tamanho (pelo menos 1 intervalo) e não ser negativas.")
    length = interval_minutes * 60.0
    capacity = np.stack([np.broadcast_to(np.asarray(g.agents, dtype=int), (n_int,)) for g in groups])  # (G, intervals)
    n_groups, n_queues = len(groups), len(names)
    can_serve = np.array([[q in g.skills for q in names] for g in groups])  # (G, Q)
    skill_count = can_serve.sum(axis=1)
    rng = np.random.default_rng(seed)

    # --- arrivals of every queue, merged and sorted by time --------------------------------------
    times, queue_of = [], []
    for qi, name in enumerate(names):
        counts = rng.poisson(expected[name])
        owner = np.repeat(np.arange(n_int), counts)
        times.append(owner * length + rng.uniform(0, length, size=owner.size))
        queue_of.append(np.full(owner.size, qi))
    arr_time = np.concatenate(times)
    arr_queue = np.concatenate(queue_of).astype(int)
    order = np.argsort(arr_time, kind="stable")
    arr_time, arr_queue = arr_time[order], arr_queue[order]
    n_calls = arr_time.size
    arr_int = np.minimum((arr_time // length).astype(int), n_int - 1) if n_calls else np.empty(0, dtype=int)
    aht = np.array([specs[n].aht_seconds for n in names])
    service = _service_times(rng, aht[arr_queue], aht_cv) if n_calls else np.empty(0)
    patience = np.array([specs[n].mean_patience_seconds or np.inf for n in names])
    patience_draw = np.where(np.isfinite(patience[arr_queue]), rng.exponential(1.0, size=n_calls) * patience[arr_queue], np.inf) if n_calls else np.empty(0)
    priority = np.array([specs[n].priority for n in names])

    # --- event loop -------------------------------------------------------------------------------
    wait = np.full(n_calls, np.nan)
    answered = np.zeros(n_calls, dtype=bool)
    abandoned = np.zeros(n_calls, dtype=bool)
    waiting = np.zeros(n_calls, dtype=bool)
    start = np.full(n_calls, np.nan)
    served_by = np.full(n_calls, -1, dtype=int)
    waiting_lines: list[deque[int]] = [deque() for _ in range(n_queues)]
    busy = np.zeros(n_groups, dtype=int)
    cap = capacity[:, 0].copy()
    heap: list[tuple[float, int, int]] = [(i * length, _CAPACITY, i) for i in range(1, n_int)]
    heapq.heapify(heap)
    nxt = 0

    def head(qi: int) -> int | None:
        line = waiting_lines[qi]
        while line and not waiting[line[0]]:
            line.popleft()  # already hung up
        return line[0] if line else None

    def begin(call: int, group: int, now: float) -> None:
        waiting[call] = False
        answered[call] = True
        wait[call] = now - arr_time[call]
        start[call] = now
        served_by[call] = group
        busy[group] += 1
        heapq.heappush(heap, (now + service[call], _COMPLETION, call))

    def fill(group: int, now: float) -> None:
        eligible = np.flatnonzero(can_serve[group])
        while busy[group] < cap[group]:
            best = None
            for qi in eligible:
                call = head(int(qi))
                if call is None:
                    continue
                key = (arr_time[call],) if routing == "longest_wait" else (priority[qi], arr_time[call])
                if best is None or key < best[0]:
                    best = (key, call)
            if best is None:
                return
            waiting_lines[arr_queue[best[1]]].popleft()
            begin(best[1], group, now)

    while nxt < n_calls or heap:
        if nxt < n_calls and (not heap or arr_time[nxt] < heap[0][0]):
            now, call = arr_time[nxt], nxt
            nxt += 1
            qi = arr_queue[call]
            free = [g for g in range(n_groups) if can_serve[g, qi] and busy[g] < cap[g]]
            if free:
                if prefer == "specialist":
                    chosen = min(free, key=lambda g: (skill_count[g], busy[g] - cap[g]))
                else:
                    chosen = min(free, key=lambda g: (-skill_count[g], busy[g] - cap[g]))
                begin(call, chosen, now)
            else:
                waiting[call] = True
                waiting_lines[qi].append(call)
                if np.isfinite(patience_draw[call]):
                    heapq.heappush(heap, (now + patience_draw[call], _ABANDON, call))
            continue
        now, kind, ref = heapq.heappop(heap)
        if kind == _CAPACITY:
            cap = capacity[:, ref].copy()
            for g in range(n_groups):
                fill(g, now)
        elif kind == _COMPLETION:
            group = served_by[ref]
            busy[group] -= 1
            fill(group, now)
        elif waiting[ref]:
            waiting[ref] = False
            abandoned[ref] = True
            wait[ref] = now - arr_time[ref]

    # --- metrics ----------------------------------------------------------------------------------
    idx = index if index is not None else pd.RangeIndex(n_int)
    per_queue: dict[str, pd.DataFrame] = {}
    for qi, name in enumerate(names):
        mine = arr_queue == qi
        threshold = specs[name].service_level_seconds

        def count(mask: np.ndarray, mine=mine) -> np.ndarray:
            return np.bincount(arr_int[mine & mask], minlength=n_int) if n_calls else np.zeros(n_int, dtype=int)

        def mean(values: np.ndarray, mask: np.ndarray, mine=mine) -> np.ndarray:
            if not n_calls:
                return np.full(n_int, np.nan)
            chosen = mine & mask
            total = np.bincount(arr_int[chosen], weights=values[chosen], minlength=n_int)
            number = np.bincount(arr_int[chosen], minlength=n_int)
            with np.errstate(invalid="ignore", divide="ignore"):
                return np.where(number > 0, total / number, np.nan)

        offered = count(np.ones(n_calls, dtype=bool))
        within = count(answered & (np.nan_to_num(wait, nan=np.inf) <= threshold))
        n_abandoned = count(abandoned)
        with np.errstate(invalid="ignore", divide="ignore"):
            per_queue[name] = pd.DataFrame(
                {
                    "offered": offered,
                    "answered": count(answered),
                    "abandoned": n_abandoned,
                    "service_level_pct": np.where(offered > 0, 100 * within / offered, np.nan),
                    "abandon_pct": np.where(offered > 0, 100 * n_abandoned / offered, np.nan),
                    "avg_wait_answered_seconds": mean(wait, answered),
                    "avg_handle_seconds": mean(service, answered),
                },
                index=idx,
            )

    boundaries = np.arange(n_int + 1) * length
    occupancy = np.full((n_int, n_groups), np.nan)
    for g in range(n_groups):
        mine = answered & (served_by == g)
        busy_start, busy_len = start[mine], service[mine]
        cumulative = np.array([np.clip(b - busy_start, 0, busy_len).sum() for b in boundaries])
        with np.errstate(invalid="ignore", divide="ignore"):
            occupancy[:, g] = np.where(capacity[g] > 0, 100 * np.diff(cumulative) / (capacity[g] * length), np.nan)
    group_names = [g.name for g in groups]
    return SkillsResult(
        per_queue,
        pd.DataFrame(capacity.T, index=idx, columns=group_names),
        pd.DataFrame(occupancy, index=idx, columns=group_names),
    )


# --- summaries and replications ---------------------------------------------------------------------
def overall_by_queue(result: SkillsResult, skip: int = 0) -> pd.DataFrame:
    """One row per queue for the whole run: calls, answered, abandoned, service level, abandonment and wait."""
    rows = {}
    for name, table in result.queues.items():
        data = table.iloc[skip:]
        offered, answered = data["offered"].sum(), data["answered"].sum()
        if offered == 0:
            rows[name] = {"offered": 0, "answered": 0, "abandoned": 0, "service_level_pct": math.nan,
                          "abandon_pct": math.nan, "avg_wait_answered_seconds": math.nan}
            continue
        rows[name] = {
            "offered": int(offered), "answered": int(answered), "abandoned": int(data["abandoned"].sum()),
            "service_level_pct": float((data["service_level_pct"].fillna(0) / 100 * data["offered"]).sum() / offered * 100),
            "abandon_pct": float(100 * data["abandoned"].sum() / offered),
            "avg_wait_answered_seconds": float((data["avg_wait_answered_seconds"].fillna(0) * data["answered"]).sum() / answered)
            if answered else math.nan,
        }
    return pd.DataFrame(rows).T


@dataclass(frozen=True)
class SkillsReplications:
    """Mean over replications with a 95% half-width, for each queue and for each agent group."""

    queues: dict[str, dict[str, tuple[float, float]]]  # queue -> metric -> (mean, half-width)
    occupancy_pct: dict[str, tuple[float, float]]  # group -> (mean, half-width)
    n_replications: int


def simulate_skills_replications(
    calls, groups, queues, interval_minutes: int, *, n_replications: int = 10, seed: int = 0,
    warmup_intervals: int = 0, **kwargs,
) -> SkillsReplications:
    """Run ``simulate_skills`` several times (seeds ``seed``, ``seed+1``...) and summarise."""
    if n_replications < 1:
        raise ValueError("n_replications deve ser pelo menos 1.")
    runs = [simulate_skills(calls, groups, queues, interval_minutes, seed=seed + r, **kwargs) for r in range(n_replications)]
    overalls = [overall_by_queue(run, warmup_intervals) for run in runs]
    names = list(runs[0].queues)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # a queue with no calls has no averages
        per_queue = {
            name: {
                metric: (float(np.nanmean([o.loc[name, metric] for o in overalls])),
                         _half_width(np.array([o.loc[name, metric] for o in overalls], dtype=float)))
                for metric in QUEUE_METRICS
            }
            for name in names
        }
        occupancy = {}
        for group in runs[0].agents.columns:
            values = np.array([
                float(np.nansum(run.occupancy_pct[group].iloc[warmup_intervals:] * run.agents[group].iloc[warmup_intervals:])
                      / max(run.agents[group].iloc[warmup_intervals:].sum(), 1))
                for run in runs
            ])
            occupancy[group] = (float(values.mean()), _half_width(values))
    return SkillsReplications(per_queue, occupancy, n_replications)
