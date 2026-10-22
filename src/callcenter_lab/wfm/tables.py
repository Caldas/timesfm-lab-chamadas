"""Results as tidy tables with Portuguese headers, shared by the interface and the exports."""

from __future__ import annotations

import pandas as pd

from .config import StaffingConfig
from .scheduling import Roster

PLAN_COLUMNS = {
    "calls": "Chamadas",
    "aht_seconds": "TMA (s)",
    "workload_erlangs": "Carga (Erlangs)",
    "agents": "Agentes",
    "service_level_pct": "Nível de serviço esperado (%)",
    "asa_seconds": "Espera média (s)",
    "occupancy_pct": "Ocupação (%)",
    "prob_wait": "Prob. de espera",
    "abandon_pct": "Abandono esperado (%)",
    "scheduled": "Pessoas escaladas",
    "cost": "Custo",
}

SCENARIO_RESULT_COLUMNS = {
    "scenario": "Cenário",
    "volume": "Volume",
    "calls_total": "Chamadas",
    "peak_agents": "Pico de agentes",
    "agent_hours": "Horas de agente",
    "peak_scheduled": "Pico de pessoas escaladas",
    "scheduled_hours": "Horas escaladas",
    "fte": "FTE",
    "expected_service_level_pct": "Nível de serviço esperado (%)",
    "cost": "Custo",
    "delta_agent_hours": "Variação de horas de agente",
    "delta_agent_hours_pct": "Variação de horas de agente (%)",
    "delta_cost": "Variação de custo",
    "roster_shortfall_intervals": "Escala: intervalos com falta",
    "roster_shortfall_person_hours": "Escala: horas de falta",
    "roster_surplus_person_hours": "Escala: horas de sobra",
}

SENSITIVITY_RESULT_COLUMNS = {
    "value": "Valor",
    "peak_agents": "Pico de agentes",
    "agent_hours": "Horas de agente",
    "scheduled_hours": "Horas escaladas",
    "fte": "FTE",
    "cost": "Custo",
    "delta_agent_hours_pct": "Variação de horas de agente (%)",
}


def _rename(frame: pd.DataFrame, names: dict[str, str]) -> pd.DataFrame:
    return frame[[c for c in names if c in frame.columns]].rename(columns=names)


def plan_table(plan: pd.DataFrame) -> pd.DataFrame:
    """The staffing plan with Portuguese headers and sensible rounding."""
    shown = _rename(plan, PLAN_COLUMNS)
    return shown.round({"TMA (s)": 0, "Carga (Erlangs)": 2, "Nível de serviço esperado (%)": 1, "Espera média (s)": 1,
                        "Ocupação (%)": 1, "Prob. de espera": 3, "Abandono esperado (%)": 1, "Chamadas": 1, "Custo": 2})


def range_table(plan_range: pd.DataFrame) -> pd.DataFrame:
    names = {
        "calls_low": "Chamadas (cenário baixo 10%)", "calls_expected": "Chamadas (esperado)",
        "calls_high": "Chamadas (cenário alto 90%)", "agents_low": "Agentes (baixo)",
        "agents_expected": "Agentes (esperado)", "agents_high": "Agentes (alto)",
        "scheduled_low": "Pessoas escaladas (baixo)", "scheduled_expected": "Pessoas escaladas (esperado)",
        "scheduled_high": "Pessoas escaladas (alto)",
    }
    return _rename(plan_range, names).round(1)


def shifts_table(roster: Roster) -> pd.DataFrame:
    names = {"date": "Dia", "shift": "Turno", "start": "Início", "end": "Fim", "people": "Pessoas",
             "paid_hours_total": "Horas pagas", "cost": "Custo"}
    shown = _rename(roster.shifts, names)
    if "Dia" in shown:
        shown["Dia"] = pd.to_datetime(shown["Dia"]).dt.strftime("%Y-%m-%d")
    return shown.round({"Horas pagas": 1, "Custo": 2})


def breaks_table(roster: Roster) -> pd.DataFrame:
    names = {"date": "Dia", "shift": "Turno", "break_start": "Início da pausa", "break_end": "Fim da pausa", "people": "Pessoas"}
    shown = _rename(roster.breaks, names)
    if "Dia" in shown:
        shown["Dia"] = pd.to_datetime(shown["Dia"]).dt.strftime("%Y-%m-%d")
    return shown


def coverage_table(roster: Roster) -> pd.DataFrame:
    names = {"needed": "Necessidade", "on_shift": "No turno", "on_break": "Em pausa", "covered": "Cobertura",
             "shortfall": "Falta", "surplus": "Sobra"}
    return _rename(roster.coverage, names).round(1)


def scenarios_result_table(result: pd.DataFrame) -> pd.DataFrame:
    return _rename(result, SCENARIO_RESULT_COLUMNS).round(1)


def sensitivity_result_table(result: pd.DataFrame) -> pd.DataFrame:
    return _rename(result, SENSITIVITY_RESULT_COLUMNS).round(2)


def config_table(config: StaffingConfig) -> pd.DataFrame:
    """The parameters as two columns (name, value), to keep next to the results."""
    s = config.shrinkage
    rows = [
        ("Intervalo (min)", config.interval_minutes),
        ("Meta de nível de serviço (%)", config.service_level_pct),
        ("Atendidas em até (s)", config.service_level_seconds),
        ("Ocupação máxima (%)", config.max_occupancy_pct),
        ("Espera média máxima (s)", "sem limite" if config.max_asa_seconds is None else config.max_asa_seconds),
        ("Paciência média (s)", "ninguém desiste (Erlang C)" if config.mean_patience_seconds is None else config.mean_patience_seconds),
        ("TMA padrão (s)", config.aht_seconds),
        ("Shrinkage: pausas (%)", s.pauses_pct),
        ("Shrinkage: treinamento (%)", s.training_pct),
        ("Shrinkage: absenteísmo (%)", s.absenteeism_pct),
        ("Shrinkage: férias (%)", s.vacation_pct),
        ("Shrinkage: outros (%)", s.other_pct),
        ("Shrinkage total (%)", s.total_pct),
        ("Custo por hora", "não calculado" if config.cost_per_hour is None else config.cost_per_hour),
        ("Horas pagas por pessoa por dia", config.shift_hours),
    ]
    return pd.DataFrame(rows, columns=["Parâmetro", "Valor"])
