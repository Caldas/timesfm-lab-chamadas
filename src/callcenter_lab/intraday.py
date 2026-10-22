"""Following the day: compare what was planned with what is arriving, and re-forecast the rest of the day.

The day is planned in the morning (a forecast made with the history *before* the day). As the day goes on
there is a *cutoff*: the intervals before it are observed, the ones from it onward are still ahead. From that
point this module

- compares planned and actual per interval, with the 10%-90% band of the plan (``plan_vs_actual``);
- flags intervals outside the band and sustained deviations (``deviation_alerts``);
- re-forecasts the remaining intervals using what already happened today (``follow_up_day``);
- projects the total of the day (actual so far + re-forecast) against the plan.

Used on past data it also answers "was re-forecasting at that time better than keeping the morning plan?",
because the remaining actuals are known.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .events import forecast_with_events
from .metrics import bias_pct, wape


def intervals_per_day(freq: str) -> int:
    """How many intervals of ``freq`` fit in one day."""
    step = pd.Timedelta(pd.tseries.frequencies.to_offset(freq))
    return round(pd.Timedelta(days=1) / step)


def alert_level(deviation_pct: float, warn_pct: float = 10.0, critical_pct: float = 20.0) -> str:
    """``"ok"``, ``"atenção"`` or ``"crítico"`` from the accumulated deviation of the day (in %, signed)."""
    if warn_pct <= 0 or critical_pct < warn_pct:
        raise ValueError("Os limites precisam ser 0 < atenção <= crítico.")
    if math.isnan(deviation_pct):
        return "ok"
    size = abs(deviation_pct)
    return "crítico" if size >= critical_pct else "atenção" if size >= warn_pct else "ok"


def plan_vs_actual(planned: pd.DataFrame, actual: pd.Series) -> pd.DataFrame:
    """Per-interval comparison for the intervals that have an actual value.

    ``planned`` has the columns ``point``, ``lower`` and ``upper``. Adds ``difference`` (actual - planned),
    ``difference_pct`` and ``position``: ``"acima"`` (above the band), ``"abaixo"`` (below) or ``"dentro"``.
    """
    observed = actual.dropna()
    table = planned.loc[planned.index.intersection(observed.index)].copy()
    table["actual"] = observed.reindex(table.index)
    table["difference"] = table["actual"] - table["point"]
    with np.errstate(invalid="ignore", divide="ignore"):
        table["difference_pct"] = np.where(table["point"] > 0, 100 * table["difference"] / table["point"], np.nan)
    table["position"] = np.where(
        table["actual"] > table["upper"], "acima", np.where(table["actual"] < table["lower"], "abaixo", "dentro")
    )
    return table


def deviation_alerts(table: pd.DataFrame, consecutive: int = 3) -> pd.DataFrame:
    """Sustained deviations: runs of at least ``consecutive`` intervals in a row outside the band, on the same side.

    One interval outside a 10%-90% band is normal (it happens 20% of the time); several in a row on the same
    side mean the day is moving away from the plan. Columns: ``start``, ``end``, ``intervals``, ``position``,
    ``planned``, ``actual``, ``difference_pct``.
    """
    if consecutive < 1:
        raise ValueError("consecutive deve ser pelo menos 1.")
    rows = []
    run_start = None
    positions = table["position"].to_numpy()
    for i in range(len(table) + 1):
        current = positions[i] if i < len(table) else "dentro"
        previous = positions[i - 1] if i > 0 else "dentro"
        if run_start is not None and (current != previous or current == "dentro"):
            run = table.iloc[run_start:i]
            if len(run) >= consecutive:
                planned, actual = float(run["point"].sum()), float(run["actual"].sum())
                rows.append({
                    "start": run.index[0], "end": run.index[-1], "intervals": len(run), "position": positions[run_start],
                    "planned": planned, "actual": actual,
                    "difference_pct": 100 * (actual - planned) / planned if planned else math.nan,
                })
            run_start = None
        if current != "dentro" and run_start is None:
            run_start = i
    return pd.DataFrame(rows, columns=["start", "end", "intervals", "position", "planned", "actual", "difference_pct"])


@dataclass(frozen=True)
class DayFollowUp:
    """Everything about one day at a given cutoff."""

    day: pd.Timestamp
    cutoff: pd.Timestamp
    plan: pd.DataFrame  # point/lower/upper for the whole day, made before the day started
    observed: pd.Series  # actuals before the cutoff
    comparison: pd.DataFrame  # plan_vs_actual on the observed intervals
    alerts: pd.DataFrame  # sustained deviations so far
    reforecast: pd.DataFrame | None  # point/lower/upper for the remaining intervals (None if the day is over)
    actual_remaining: pd.Series | None  # known only when studying past data
    summary: dict[str, float | str]


def follow_up_day(
    forecaster,
    series: pd.Series,
    day,
    cutoff,
    freq: str,
    events: pd.DataFrame | None = None,
    event_mode: str = "adjust",
    warn_pct: float = 10.0,
    critical_pct: float = 20.0,
    consecutive: int = 3,
) -> DayFollowUp:
    """Plan the day with the history before it, observe it up to ``cutoff`` and re-forecast the rest.

    ``series`` has the calls per interval; it may end at the cutoff (a day in progress) or go beyond it (a
    past day, which lets the plan and the re-forecast be scored on what really happened). ``cutoff`` is the
    first interval that is not yet known: with data up to 10:30 inclusive, the cutoff is 11:00.
    """
    day = pd.Timestamp(day).normalize()
    cutoff = pd.Timestamp(cutoff)
    n_day = intervals_per_day(freq)
    day_index = pd.date_range(day, periods=n_day, freq=freq)
    step = pd.Timedelta(pd.tseries.frequencies.to_offset(freq))
    if not day_index[0] <= cutoff <= day_index[-1] + step:
        raise ValueError("O horário de corte precisa estar dentro do dia.")
    history = series[series.index < day]
    if len(history) < 2:
        raise ValueError("Não há histórico antes desse dia para planejá-lo.")

    plan_result = forecast_with_events(forecaster, history, n_day, freq, events, event_mode)
    plan = pd.DataFrame({"point": plan_result.point, "lower": plan_result.lower, "upper": plan_result.upper}, index=day_index)

    observed = series[(series.index >= day) & (series.index < cutoff)]
    comparison = plan_vs_actual(plan, observed)
    alerts = deviation_alerts(comparison, consecutive)

    remaining_index = day_index[day_index >= cutoff]
    reforecast = actual_remaining = None
    if len(remaining_index):
        known = series[series.index < cutoff]
        result = forecast_with_events(forecaster, known, len(remaining_index), freq, events, event_mode)
        reforecast = pd.DataFrame({"point": result.point, "lower": result.lower, "upper": result.upper}, index=remaining_index)
        future_actual = series.reindex(remaining_index)
        actual_remaining = future_actual if future_actual.notna().any() else None

    planned_so_far = float(comparison["point"].sum())
    actual_so_far = float(comparison["actual"].sum())
    deviation = 100 * (actual_so_far - planned_so_far) / planned_so_far if planned_so_far > 0 else math.nan
    summary: dict[str, float | str] = {
        "intervals_observed": len(comparison),
        "planned_so_far": planned_so_far,
        "actual_so_far": actual_so_far,
        "deviation_pct": deviation,
        "alert": alert_level(deviation, warn_pct, critical_pct),
        "intervals_above": int((comparison["position"] == "acima").sum()),
        "intervals_below": int((comparison["position"] == "abaixo").sum()),
        "wape_so_far": wape(comparison["actual"], comparison["point"]) if len(comparison) else math.nan,
        "bias_so_far": bias_pct(comparison["actual"], comparison["point"]) if len(comparison) else math.nan,
        "plan_total": float(plan["point"].sum()),
    }
    if reforecast is not None:
        summary["projected_total"] = actual_so_far + float(reforecast["point"].sum())
        summary["projected_difference_pct"] = (
            100 * (summary["projected_total"] - summary["plan_total"]) / summary["plan_total"]
            if summary["plan_total"] > 0 else math.nan
        )
        if actual_remaining is not None:
            mask = actual_remaining.notna()
            truth = actual_remaining[mask]
            summary["plan_wape_remaining"] = wape(truth, plan["point"].reindex(truth.index))
            summary["reforecast_wape_remaining"] = wape(truth, reforecast["point"].reindex(truth.index))
            summary["plan_bias_remaining"] = bias_pct(truth, plan["point"].reindex(truth.index))
            summary["reforecast_bias_remaining"] = bias_pct(truth, reforecast["point"].reindex(truth.index))
    return DayFollowUp(day, cutoff, plan, observed, comparison, alerts, reforecast, actual_remaining, summary)
