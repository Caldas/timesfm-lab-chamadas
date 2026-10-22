"""Shift scheduling: how many people to put on each shift, each day, to cover the staffing need.

The need per interval is the number of people who must be *at work* (the ``scheduled`` column of
the staffing plan, which already includes shrinkage). A roster covers it with shift templates:

- a template has a start, a length, the weekdays it is offered and an optional meal break that
  must start inside a window; breaks are staggered by the optimiser, so coverage dips are small;
- coverage at an interval = people on shift - people on their meal break;
- the short breaks, training, absenteeism and vacation stay in the *shrinkage* of the plan. If your
  shrinkage "pauses" already includes lunch, lower it or use templates with no meal break.

The problem is solved exactly as a mixed-integer program (scipy's HiGHS solver). Missing coverage is
allowed but very expensive, so a roster that cannot cover everything (for example because of
``max_people`` or ``max_headcount``) still comes back, with the shortfall reported.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .config import StaffingConfig
from .simulator import ReplicationResult, simulate_replications

WEEKDAYS = ("seg", "ter", "qua", "qui", "sex", "sab", "dom")


@dataclass(frozen=True)
class ShiftTemplate:
    """One kind of shift. ``days`` are weekdays it is offered on (0 = Monday ... 6 = Sunday)."""

    name: str
    start: str  # "HH:MM"
    hours: float  # length on site, meal break included
    days: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6)
    meal_break_minutes: int = 0
    meal_window_hours: tuple[float, float] = (3.0, 5.0)  # the break must START between these hours after the start
    min_people: int = 0  # if the shift is used on a day, at least this many people
    max_people: int | None = None  # at most this many people per day
    max_on_break_pct: float = 100.0  # at most this share of the shift on break at the same time
    cost_per_hour: float | None = None  # overrides the default cost
    meal_break_paid: bool = False

    def __post_init__(self) -> None:
        if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", self.start):
            raise ValueError(f"Início inválido em '{self.name}': use HH:MM (recebi {self.start!r}).")
        if not 0 < self.hours <= 24:
            raise ValueError(f"As horas de '{self.name}' devem estar entre 0 (exclusive) e 24.")
        if not self.days or any(d not in range(7) for d in self.days):
            raise ValueError(f"Os dias de '{self.name}' devem ser números de 0 (segunda) a 6 (domingo).")
        if self.meal_break_minutes < 0:
            raise ValueError(f"A pausa de refeição de '{self.name}' não pode ser negativa.")
        low, high = self.meal_window_hours
        if self.meal_break_minutes and not (0 <= low <= high and high * 60 + self.meal_break_minutes <= self.hours * 60):
            raise ValueError(f"A janela da pausa de '{self.name}' precisa caber dentro do turno.")
        if self.min_people < 0 or (self.max_people is not None and self.max_people < max(self.min_people, 1)):
            raise ValueError(f"Mínimo/máximo de pessoas inválidos em '{self.name}'.")
        if not 0 < self.max_on_break_pct <= 100:
            raise ValueError(f"max_on_break_pct de '{self.name}' deve estar entre 0 (exclusive) e 100.")
        if self.cost_per_hour is not None and self.cost_per_hour < 0:
            raise ValueError(f"O custo por hora de '{self.name}' não pode ser negativo.")

    @property
    def start_minutes(self) -> int:
        hh, mm = self.start.split(":")
        return int(hh) * 60 + int(mm)

    @property
    def paid_hours(self) -> float:
        return self.hours - (0 if self.meal_break_paid else self.meal_break_minutes / 60)


@dataclass(frozen=True)
class RosterRules:
    """Rules that apply to the whole roster."""

    max_days_per_week: int = 5  # each person works at most this many days in a 7-day week
    max_headcount: int | None = None  # people available; None = as many as needed
    time_limit_seconds: float = 30.0
    default_cost_per_hour: float = 1.0  # used by templates without their own cost

    def __post_init__(self) -> None:
        if not 1 <= self.max_days_per_week <= 7:
            raise ValueError("max_days_per_week deve estar entre 1 e 7.")
        if self.max_headcount is not None and self.max_headcount < 1:
            raise ValueError("max_headcount deve ser pelo menos 1 (ou None).")
        if self.time_limit_seconds <= 0 or self.default_cost_per_hour < 0:
            raise ValueError("time_limit_seconds deve ser > 0 e o custo não pode ser negativo.")


@dataclass(frozen=True)
class Roster:
    """The optimised roster: who works when, breaks, coverage and cost."""

    shifts: pd.DataFrame  # one row per day and shift used
    breaks: pd.DataFrame  # meal break start times and how many people take them
    coverage: pd.DataFrame  # per interval: needed, on_shift, on_break, covered, shortfall, surplus
    headcount: int  # people needed to respect the days-off rule
    cost: float
    status: str
    interval_minutes: int
    templates: tuple[ShiftTemplate, ...] = field(default_factory=tuple)

    def summary(self) -> dict[str, float]:
        hours = self.interval_minutes / 60
        cov = self.coverage
        needed = cov["needed"] > 0
        return {
            "headcount": self.headcount,
            "cost": self.cost,
            "paid_hours": float(self.shifts["paid_hours_total"].sum()) if len(self.shifts) else 0.0,
            "shortfall_intervals": int((cov["shortfall"] > 0).sum()),
            "shortfall_person_hours": float(cov["shortfall"].sum() * hours),
            "surplus_person_hours": float(cov["surplus"].sum() * hours),
            "fully_covered_pct": float(100 * (cov.loc[needed, "shortfall"] == 0).mean()) if needed.any() else 100.0,
        }


# --- templates as tables (for the interface and for files) -------------------------------------
TABLE_COLUMNS = ["nome", "início", "horas", "dias", "refeição_min", "janela_início_h", "janela_fim_h",
                 "mín_pessoas", "máx_pessoas", "máx_em_pausa_%", "custo_hora", "refeição_paga"]


def parse_days(text: str) -> tuple[int, ...]:
    """'seg-sex, dom' -> (0, 1, 2, 3, 4, 6). Accepts ranges and comma/space separated names."""
    days: set[int] = set()
    for part in re.split(r"[,\s]+", str(text).strip().lower()):
        if not part:
            continue
        if "-" in part:
            first, last = part.split("-", 1)
            if first not in WEEKDAYS or last not in WEEKDAYS:
                raise ValueError(f"Dia inválido: {part!r}. Use {', '.join(WEEKDAYS)}.")
            a, b = WEEKDAYS.index(first), WEEKDAYS.index(last)
            days.update(range(a, b + 1) if a <= b else [*range(a, 7), *range(b + 1)])
        elif part in WEEKDAYS:
            days.add(WEEKDAYS.index(part))
        else:
            raise ValueError(f"Dia inválido: {part!r}. Use {', '.join(WEEKDAYS)}.")
    if not days:
        raise ValueError("Informe pelo menos um dia (ex.: seg-sex).")
    return tuple(sorted(days))


def format_days(days: tuple[int, ...]) -> str:
    """(0, 1, 2, 3, 4) -> 'seg-sex'; (5,) -> 'sab'; (0, 2) -> 'seg, qua'."""
    ordered = sorted(set(days))
    runs: list[tuple[int, int]] = []
    first = last = ordered[0]
    for day in ordered[1:]:
        if day == last + 1:
            last = day
            continue
        runs.append((first, last))
        first = last = day
    runs.append((first, last))
    return ", ".join(WEEKDAYS[a] if a == b else f"{WEEKDAYS[a]}-{WEEKDAYS[b]}" for a, b in runs)


def templates_to_table(templates) -> pd.DataFrame:
    rows = [
        {
            "nome": t.name, "início": t.start, "horas": t.hours, "dias": format_days(t.days),
            "refeição_min": t.meal_break_minutes, "janela_início_h": t.meal_window_hours[0],
            "janela_fim_h": t.meal_window_hours[1], "mín_pessoas": t.min_people,
            "máx_pessoas": t.max_people, "máx_em_pausa_%": t.max_on_break_pct,
            "custo_hora": t.cost_per_hour, "refeição_paga": t.meal_break_paid,
        }
        for t in templates
    ]
    return pd.DataFrame(rows, columns=TABLE_COLUMNS)


def templates_from_table(table: pd.DataFrame) -> list[ShiftTemplate]:
    """Read the table back. Blank cells use the defaults; invalid rows raise ValueError."""
    def value(row, column, default):
        item = row.get(column)
        return default if item is None or (isinstance(item, float) and math.isnan(item)) or item == "" else item

    templates = []
    for _, row in table.iterrows():
        if not str(value(row, "nome", "")).strip():
            continue
        max_people = value(row, "máx_pessoas", None)
        cost = value(row, "custo_hora", None)
        templates.append(
            ShiftTemplate(
                name=str(row["nome"]).strip(),
                start=str(value(row, "início", "08:00")).strip(),
                hours=float(value(row, "horas", 8)),
                days=parse_days(value(row, "dias", "seg-dom")),
                meal_break_minutes=int(value(row, "refeição_min", 0)),
                meal_window_hours=(float(value(row, "janela_início_h", 3.0)), float(value(row, "janela_fim_h", 5.0))),
                min_people=int(value(row, "mín_pessoas", 0)),
                max_people=None if max_people is None else int(max_people),
                max_on_break_pct=float(value(row, "máx_em_pausa_%", 100.0)),
                cost_per_hour=None if cost is None else float(cost),
                meal_break_paid=bool(value(row, "refeição_paga", False)),
            )
        )
    if not templates:
        raise ValueError("Informe pelo menos um turno.")
    return templates


def example_templates() -> list[ShiftTemplate]:
    """Example shifts (weekdays 8h-20h plus a short Saturday). Not a reference for any operation."""
    weekdays = (0, 1, 2, 3, 4)
    return [
        ShiftTemplate("Manhã 08–16h", "08:00", 8, weekdays, meal_break_minutes=60, meal_window_hours=(3.0, 5.0)),
        ShiftTemplate("Intermediário 10–18h", "10:00", 8, weekdays, meal_break_minutes=60, meal_window_hours=(3.0, 5.0)),
        ShiftTemplate("Tarde 12–20h", "12:00", 8, weekdays, meal_break_minutes=60, meal_window_hours=(3.0, 5.0)),
        ShiftTemplate("Sábado 08–14h", "08:00", 6, (5,)),
    ]


# --- the optimiser -------------------------------------------------------------------------------
def _grid(needed: pd.Series, interval_minutes: int) -> tuple[pd.DatetimeIndex, np.ndarray, int, int]:
    if not isinstance(needed.index, pd.DatetimeIndex) or len(needed) == 0:
        raise ValueError("A necessidade precisa ser uma série com índice de data/hora.")
    per_day = 1440 // interval_minutes
    first = needed.index[0].normalize()
    days = (needed.index[-1].normalize() - first).days + 1
    index = pd.date_range(first, periods=days * per_day, freq=f"{interval_minutes}min")
    values = needed.reindex(index).fillna(0).clip(lower=0).to_numpy(dtype=float)
    return index, values, days, per_day


def _in_intervals(minutes: float, interval_minutes: int, what: str) -> int:
    value = minutes / interval_minutes
    if abs(value - round(value)) > 1e-9:
        raise ValueError(f"{what} ({minutes:g} min) precisa ser múltiplo do intervalo ({interval_minutes} min).")
    return round(value)


def optimize_roster(
    needed: pd.Series, templates, interval_minutes: int, rules: RosterRules | None = None
) -> Roster:
    """Choose, for each day, how many people work each shift so that coverage meets ``needed`` at minimum cost."""
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import coo_matrix

    rules = rules or RosterRules()
    templates = list(templates)
    if not templates:
        raise ValueError("Informe pelo menos um turno.")
    if 1440 % interval_minutes:
        raise ValueError("O intervalo precisa dividir um dia em partes iguais.")
    index, need, n_days, per_day = _grid(needed, interval_minutes)
    n_total = len(index)
    first_weekday = index[0].day_of_week

    # per template, in intervals
    spec = []
    for t in templates:
        length = _in_intervals(t.hours * 60, interval_minutes, f"A duração de '{t.name}'")
        offset = _in_intervals(t.start_minutes, interval_minutes, f"O início de '{t.name}'")
        meal = _in_intervals(t.meal_break_minutes, interval_minutes, f"A pausa de '{t.name}'") if t.meal_break_minutes else 0
        options: list[int] = []
        if meal:
            lo = math.ceil(t.meal_window_hours[0] * 60 / interval_minutes - 1e-9)
            hi = math.floor(t.meal_window_hours[1] * 60 / interval_minutes + 1e-9)
            options = [k for k in range(lo, hi + 1) if k + meal <= length]
            if not options:
                raise ValueError(f"A janela da pausa de '{t.name}' não tem horários possíveis com o intervalo escolhido.")
        spec.append({"t": t, "length": length, "offset": offset, "meal": meal, "options": options})

    ub_default = math.ceil(need.max() * 2) + 5 if need.max() > 0 else 5
    var_names: list[tuple] = []
    lower: list[float] = []
    upper: list[float] = []
    integer: list[int] = []
    cost: list[float] = []

    def add_var(name, lb, ub, is_int, c):
        var_names.append(name)
        lower.append(lb)
        upper.append(ub)
        integer.append(1 if is_int else 0)
        cost.append(c)
        return len(var_names) - 1

    x_idx: dict[tuple[int, int], int] = {}
    y_idx: dict[tuple[int, int, int], int] = {}
    z_idx: dict[tuple[int, int], int] = {}
    for d in range(n_days):
        weekday = (first_weekday + d) % 7
        for s, sp in enumerate(spec):
            t = sp["t"]
            if weekday not in t.days:
                continue
            rate = t.cost_per_hour if t.cost_per_hour is not None else rules.default_cost_per_hour
            ub = t.max_people if t.max_people is not None else ub_default
            x_idx[(d, s)] = add_var(("x", d, s), 0, ub, True, rate * t.paid_hours)
            for k in sp["options"]:
                y_idx[(d, s, k)] = add_var(("y", d, s, k), 0, ub, True, 0.0)
            if t.min_people >= 1:
                z_idx[(d, s)] = add_var(("z", d, s), 0, 1, True, 0.0)
    max_rate = max([t.cost_per_hour if t.cost_per_hour is not None else rules.default_cost_per_hour for t in templates] + [1e-6])
    penalty = 1000.0 * max_rate * (interval_minutes / 60) * 24  # missing one person for an interval costs more than a whole day of work
    u_idx: dict[int, int] = {g: add_var(("u", g), 0, np.inf, False, penalty) for g in range(n_total) if need[g] > 0}
    h_idx = add_var(("H",), 0, rules.max_headcount if rules.max_headcount is not None else np.inf, True, 1e-3 * max_rate)

    rows: list[int] = []
    cols: list[int] = []
    vals: list[float] = []
    lo_b: list[float] = []
    hi_b: list[float] = []

    def new_row(lb, ub):
        lo_b.append(lb)
        hi_b.append(ub)
        return len(lo_b) - 1

    def put(row, col, val):
        rows.append(row)
        cols.append(col)
        vals.append(val)

    cover_row = {g: new_row(float(need[g]), np.inf) for g in u_idx}
    for g, var in u_idx.items():
        put(cover_row[g], var, 1.0)

    for (d, s), xv in x_idx.items():
        sp, t = spec[s], spec[s]["t"]
        start = d * per_day + sp["offset"]
        shift_range = range(max(start, 0), min(start + sp["length"], n_total))
        for g in shift_range:
            if g in cover_row:
                put(cover_row[g], xv, 1.0)
        if sp["options"]:
            link = new_row(0.0, 0.0)
            put(link, xv, -1.0)
            for k in sp["options"]:
                yv = y_idx[(d, s, k)]
                put(link, yv, 1.0)
                for g in range(max(start + k, 0), min(start + k + sp["meal"], n_total)):
                    if g in cover_row:
                        put(cover_row[g], yv, -1.0)
            if t.max_on_break_pct < 100:
                for g in shift_range:
                    members = [(k, y_idx[(d, s, k)]) for k in sp["options"] if start + k <= g < start + k + sp["meal"]]
                    if members:
                        r = new_row(-np.inf, 0.0)
                        for _, yv in members:
                            put(r, yv, 1.0)
                        put(r, xv, -t.max_on_break_pct / 100)
        if (d, s) in z_idx:
            zv = z_idx[(d, s)]
            big = t.max_people if t.max_people is not None else ub_default
            upper_row = new_row(-np.inf, 0.0)
            put(upper_row, xv, 1.0)
            put(upper_row, zv, -float(big))
            lower_row = new_row(-np.inf, 0.0)
            put(lower_row, zv, float(t.min_people))
            put(lower_row, xv, -1.0)

    # people: one shift per person per day, and at most max_days_per_week days in a week
    for d in range(n_days):
        day_vars = [xv for (dd, _), xv in x_idx.items() if dd == d]
        if day_vars:
            r = new_row(-np.inf, 0.0)
            for xv in day_vars:
                put(r, xv, 1.0)
            put(r, h_idx, -1.0)
    for week in range(math.ceil(n_days / 7)):
        week_days = range(week * 7, min((week + 1) * 7, n_days))
        if len(week_days) > rules.max_days_per_week:
            r = new_row(-np.inf, 0.0)
            for (dd, _), xv in x_idx.items():
                if dd in week_days:
                    put(r, xv, 1.0)
            put(r, h_idx, -float(rules.max_days_per_week))

    matrix = coo_matrix((vals, (rows, cols)), shape=(len(lo_b), len(var_names))).tocsr()
    result = milp(
        c=np.array(cost),
        constraints=LinearConstraint(matrix, np.array(lo_b), np.array(hi_b)),
        integrality=np.array(integer),
        bounds=Bounds(np.array(lower), np.array(upper)),
        options={"time_limit": rules.time_limit_seconds, "mip_rel_gap": 1e-4},
    )
    if result.x is None:
        raise RuntimeError(f"O solver não achou solução: {result.message}")
    solution = np.rint(result.x).astype(int)
    status = "ótima" if result.status == 0 else "melhor encontrada no limite de tempo"

    # --- build the outputs from the integer solution -----------------------------------------
    on_shift = np.zeros(n_total)
    on_break = np.zeros(n_total)
    shift_rows, break_rows = [], []
    total_cost = 0.0
    for (d, s), xv in x_idx.items():
        people = int(solution[xv])
        if people == 0:
            continue
        sp, t = spec[s], spec[s]["t"]
        start = d * per_day + sp["offset"]
        day = index[0] + pd.Timedelta(days=d)
        begin = day + pd.Timedelta(minutes=t.start_minutes)
        end = begin + pd.Timedelta(hours=t.hours)
        on_shift[max(start, 0):min(start + sp["length"], n_total)] += people
        rate = t.cost_per_hour if t.cost_per_hour is not None else rules.default_cost_per_hour
        shift_cost = people * t.paid_hours * rate
        total_cost += shift_cost
        shift_rows.append({
            "date": day.normalize(), "shift": t.name, "start": begin, "end": end, "people": people,
            "paid_hours_total": people * t.paid_hours, "cost": shift_cost,
        })
        for k in sp["options"]:
            count = int(solution[y_idx[(d, s, k)]])
            if count:
                on_break[max(start + k, 0):min(start + k + sp["meal"], n_total)] += count
                b0 = begin + pd.Timedelta(minutes=k * interval_minutes)
                break_rows.append({"date": day.normalize(), "shift": t.name, "break_start": b0,
                                   "break_end": b0 + pd.Timedelta(minutes=t.meal_break_minutes), "people": count})
    covered = on_shift - on_break
    coverage = pd.DataFrame(
        {"needed": need, "on_shift": on_shift, "on_break": on_break, "covered": covered,
         "shortfall": np.maximum(need - covered, 0), "surplus": np.maximum(covered - need, 0)},
        index=index,
    )
    shifts = pd.DataFrame(shift_rows, columns=["date", "shift", "start", "end", "people", "paid_hours_total", "cost"])
    breaks = pd.DataFrame(break_rows, columns=["date", "shift", "break_start", "break_end", "people"])
    daily_peak = shifts.groupby("date")["people"].sum().max() if len(shifts) else 0
    headcount = int(max(solution[h_idx], daily_peak))
    return Roster(shifts, breaks, coverage, headcount, float(total_cost), status, interval_minutes, tuple(templates))


# --- checking a roster with the simulator ----------------------------------------------------------
def effective_agents(roster: Roster, plan: pd.DataFrame, config: StaffingConfig) -> np.ndarray:
    """Agents on the phones the roster gives per plan interval: covered people minus shrinkage, rounded down."""
    covered = roster.coverage["covered"].reindex(plan.index).fillna(0).to_numpy()
    return np.floor(covered * (1 - config.shrinkage.total_pct / 100) + 1e-9).astype(int)


def evaluate_roster(
    roster: Roster, plan: pd.DataFrame, config: StaffingConfig, n_replications: int = 10, seed: int = 0
) -> ReplicationResult:
    """Simulate the call center with the agents this roster actually provides."""
    return simulate_replications(
        plan["calls"].to_numpy(), effective_agents(roster, plan, config), plan["aht_seconds"].to_numpy(),
        config.interval_minutes, n_replications=n_replications, seed=seed,
        mean_patience_seconds=config.mean_patience_seconds, service_level_seconds=config.service_level_seconds,
    )
