"""Erlang C and Erlang A: how many agents does a queue need for a service-level goal?

Terms (all rates per interval are converted to seconds):
- ``load`` (A): workload in Erlangs = calls per second x average handling time (AHT, seconds).
- ``agents`` (N): agents on the phones, all equal and answering one call at a time.
- Erlang C assumes callers wait as long as needed. Erlang A also lets callers hang up after an
  exponentially distributed patience, so it needs fewer agents when there is abandonment.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .config import StaffingConfig
from .shrinkage import scheduled_headcount

_EPS = 1e-12


# --- Erlang C ---------------------------------------------------------------------------------
def erlang_b(agents: int, load: float) -> float:
    """Blocking probability, computed with the stable recursion B(n) = A*B(n-1) / (n + A*B(n-1))."""
    if agents < 0 or load < 0:
        raise ValueError("agents e load não podem ser negativos.")
    b = 1.0
    for n in range(1, int(agents) + 1):
        b = load * b / (n + load * b)
    return b


def erlang_c(agents: int, load: float) -> float:
    """Probability that an arriving call has to wait (Erlang C). It is 1.0 when agents <= load."""
    if agents < 0 or load < 0:
        raise ValueError("agents e load não podem ser negativos.")
    if load == 0:
        return 0.0
    if agents <= load:
        return 1.0
    b = erlang_b(agents, load)
    return float(agents * b / (agents - load * (1 - b)))


def service_level(agents: int, load: float, aht_seconds: float, threshold_seconds: float) -> float:
    """Share (0-1) of calls answered within ``threshold_seconds`` (Erlang C)."""
    if load == 0:
        return 1.0
    if agents <= load:
        return 0.0
    c = erlang_c(agents, load)
    return float(1 - c * math.exp(-(agents - load) * threshold_seconds / aht_seconds))


def asa(agents: int, load: float, aht_seconds: float) -> float:
    """Average speed of answer in seconds over all calls (Erlang C). Infinite when agents <= load."""
    if load == 0:
        return 0.0
    if agents <= load:
        return math.inf
    return float(erlang_c(agents, load) * aht_seconds / (agents - load))


def occupancy(agents: int, load: float) -> float:
    """Share (0-1) of agent time spent handling calls."""
    if agents <= 0:
        return 0.0 if load == 0 else math.inf
    return float(load / agents)


def required_agents(
    load: float,
    aht_seconds: float,
    service_level_pct: float,
    service_level_seconds: float,
    max_occupancy_pct: float = 100.0,
    max_asa_seconds: float | None = None,
    max_agents: int = 100_000,
) -> int:
    """Smallest number of agents (Erlang C) that meets the service-level goal and the occupancy cap."""
    if load < 0 or aht_seconds <= 0:
        raise ValueError("load não pode ser negativo e aht_seconds deve ser maior que zero.")
    if load == 0:
        return 0
    target = service_level_pct / 100
    n = max(math.floor(load) + 1, math.ceil(load / (max_occupancy_pct / 100) - _EPS))
    while n <= max_agents:
        ok = service_level(n, load, aht_seconds, service_level_seconds) >= target - _EPS
        ok = ok and occupancy(n, load) <= max_occupancy_pct / 100 + _EPS
        if ok and max_asa_seconds is not None:
            ok = asa(n, load, aht_seconds) <= max_asa_seconds + _EPS
        if ok:
            return n
        n += 1
    raise ValueError(f"Não achei uma equipe de até {max_agents} agentes que cumpra a meta para carga {load:.1f} Erlangs.")


# --- Erlang A (with abandonment) --------------------------------------------------------------
def _state_probabilities(agents: int, rate: float, aht_seconds: float, patience_seconds: float) -> np.ndarray:
    """Stationary distribution of the number of calls in the system (M/M/N+M), truncated and normalised."""
    mu, theta = 1 / aht_seconds, 1 / patience_seconds
    max_states = int(agents + max(200, 50 * math.sqrt(max(rate / theta, 1.0)) + 20 * (rate / mu) ** 0.5))
    n = np.arange(1, max_states + 1)
    death = np.minimum(n, agents) * mu + np.maximum(n - agents, 0) * theta
    log_p = np.concatenate([[0.0], np.cumsum(np.log(rate) - np.log(death))])
    log_p -= log_p.max()
    p = np.exp(log_p)
    return p / p.sum()


def erlang_a(
    agents: int, load: float, aht_seconds: float, patience_seconds: float, threshold_seconds: float
) -> dict[str, float]:
    """Metrics of a queue where callers hang up after an exponential patience (Erlang A).

    Returns ``service_level`` (answered within the threshold / all offered calls), ``abandon_prob``,
    ``prob_wait``, ``avg_wait_seconds`` (over all callers, abandoned ones included) and ``occupancy``.
    """
    if agents < 0 or load < 0 or aht_seconds <= 0 or patience_seconds <= 0:
        raise ValueError("Parâmetros inválidos para o Erlang A.")
    if load == 0:
        return {"service_level": 1.0, "abandon_prob": 0.0, "prob_wait": 0.0, "avg_wait_seconds": 0.0, "occupancy": 0.0}
    if agents == 0:
        return {"service_level": 0.0, "abandon_prob": 1.0, "prob_wait": 1.0, "avg_wait_seconds": patience_seconds, "occupancy": 0.0}

    rate = load / aht_seconds  # calls per second
    mu, theta = 1 / aht_seconds, 1 / patience_seconds
    p = _state_probabilities(agents, rate, aht_seconds, patience_seconds)
    queue = np.maximum(np.arange(len(p)) - agents, 0)
    mean_queue = float((queue * p).sum())
    abandon_prob = min(1.0, theta * mean_queue / rate)
    prob_wait = float(p[agents:].sum())

    # P(served within t | k calls ahead): uniformisation of the chain "calls ahead of me"
    k_states = len(p) - agents  # k = 0 .. k_states-1
    j = np.arange(k_states)
    down = agents * mu + j * theta  # rate of moving one place forward
    big_lambda = agents * mu + k_states * theta + theta
    t = threshold_seconds
    x = np.zeros(k_states)  # x_m[j] = P(served | start at j) after m uniformised steps
    served_by_t = np.zeros(k_states)
    mean_steps = big_lambda * t
    max_steps = int(mean_steps + 10 * math.sqrt(mean_steps + 1) + 30)
    stay = 1 - (down + theta) / big_lambda
    for m in range(max_steps + 1):
        weight = math.exp(-mean_steps + m * math.log(mean_steps) - math.lgamma(m + 1)) if mean_steps > 0 else float(m == 0)
        served_by_t += weight * x  # x_0 = 0 for the transient states
        # advance one uniformised step
        new_x = stay * x
        new_x[1:] += (down[1:] / big_lambda) * x[:-1]
        new_x[0] += (agents * mu / big_lambda) * 1.0  # from head of the queue straight into service
        x = new_x
    # The Poisson mass beyond max_steps (< 1e-9) is counted as 'not served': a negligible underestimate.
    answered_immediately = float(p[:agents].sum())
    answered_after_wait = float((p[agents:] * served_by_t[: len(p) - agents]).sum())
    sl = min(1.0, answered_immediately + answered_after_wait)
    busy = load * (1 - abandon_prob)
    return {
        "service_level": float(sl),
        "abandon_prob": float(abandon_prob),
        "prob_wait": prob_wait,
        "avg_wait_seconds": float(mean_queue / rate),
        "occupancy": float(busy / agents),
    }


def required_agents_erlang_a(
    load: float,
    aht_seconds: float,
    patience_seconds: float,
    service_level_pct: float,
    service_level_seconds: float,
    max_occupancy_pct: float = 100.0,
    max_asa_seconds: float | None = None,
) -> int:
    """Smallest number of agents that meets the goal when callers can hang up (Erlang A)."""
    if load == 0:
        return 0
    target = service_level_pct / 100

    def meets(n: int) -> bool:
        r = erlang_a(n, load, aht_seconds, patience_seconds, service_level_seconds)
        ok = r["service_level"] >= target - 1e-9 and r["occupancy"] <= max_occupancy_pct / 100 + _EPS
        if ok and max_asa_seconds is not None:
            ok = r["avg_wait_seconds"] <= max_asa_seconds + _EPS
        return ok

    hi = required_agents(load, aht_seconds, service_level_pct, service_level_seconds, max_occupancy_pct, max_asa_seconds)
    while not meets(hi):  # abandonment can, rarely, make the goal harder than Erlang C says
        hi += 1
        if hi > 100_000:
            raise ValueError("Não achei uma equipe que cumpra a meta com abandono.")
    lo = 1
    while lo < hi:  # service level grows with agents, so a binary search is enough
        mid = (lo + hi) // 2
        if meets(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo


# --- All intervals at once --------------------------------------------------------------------
def size_staffing(loads, aht_seconds, config: StaffingConfig, index: pd.DatetimeIndex | None = None) -> pd.DataFrame:
    """Agents, expected service level, ASA and occupancy for each interval.

    ``loads`` is the workload in Erlangs per interval; ``aht_seconds`` a number or an array of the same
    length. If ``config.mean_patience_seconds`` is set, Erlang A is used; otherwise Erlang C.
    Adds ``scheduled`` (people to schedule, after shrinkage) using the configured shrinkage.
    """
    loads = np.asarray(loads, dtype=float)
    aht = np.broadcast_to(np.asarray(aht_seconds, dtype=float), loads.shape)
    rows = []
    for load, handle in zip(loads, aht):
        if config.mean_patience_seconds is None:
            n = required_agents(
                load, handle, config.service_level_pct, config.service_level_seconds,
                config.max_occupancy_pct, config.max_asa_seconds,
            )
            rows.append(
                {
                    "agents": n,
                    "service_level_pct": 100 * service_level(n, load, handle, config.service_level_seconds),
                    "asa_seconds": asa(n, load, handle),
                    "occupancy_pct": 100 * occupancy(n, load),
                    "prob_wait": erlang_c(n, load),
                    "abandon_pct": 0.0,
                }
            )
        else:
            n = required_agents_erlang_a(
                load, handle, config.mean_patience_seconds, config.service_level_pct,
                config.service_level_seconds, config.max_occupancy_pct, config.max_asa_seconds,
            )
            r = erlang_a(n, load, handle, config.mean_patience_seconds, config.service_level_seconds)
            rows.append(
                {
                    "agents": n,
                    "service_level_pct": 100 * r["service_level"],
                    "asa_seconds": r["avg_wait_seconds"],
                    "occupancy_pct": 100 * r["occupancy"],
                    "prob_wait": r["prob_wait"],
                    "abandon_pct": 100 * r["abandon_prob"],
                }
            )
    out = pd.DataFrame(rows, index=index)
    out["scheduled"] = scheduled_headcount(out["agents"], config.shrinkage.total_pct)
    return out
