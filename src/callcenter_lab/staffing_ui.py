"""Streamlit pieces for staffing: the configuration panel and the "Dimensionamento" tab."""

from __future__ import annotations

import json
from collections.abc import Callable

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .wfm import (
    PRESET_LABELS,
    PRESETS,
    VALID_INTERVALS,
    ConstantAHT,
    ShrinkageConfig,
    StaffingConfig,
    build_plan,
    build_plan_range,
    daily_summary,
    load_aht_csv,
    simulate_replications,
    synthetic_aht,
)
from .wfm.workload import SeriesAHT

# widget key -> (StaffingConfig field or shrinkage component, default shown in the panel)
_KEYS = {
    "cfg_sl_pct": 80.0,
    "cfg_sl_sec": 20.0,
    "cfg_occ": 85.0,
    "cfg_asa_on": False,
    "cfg_asa": 30.0,
    "cfg_pat_on": False,
    "cfg_pat": 120.0,
    "cfg_aht": 300.0,
    "cfg_shr_pauses": 10.0,
    "cfg_shr_training": 3.0,
    "cfg_shr_absent": 5.0,
    "cfg_shr_vacation": 5.0,
    "cfg_shr_other": 2.0,
    "cfg_cost_on": False,
    "cfg_cost": 25.0,
    "cfg_shift": 8.0,
}

DISPLAY_COLUMNS = {
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


# --- configuration panel -------------------------------------------------------------------------
def _config_to_state(config: StaffingConfig) -> None:
    """Copy a configuration into the widgets' state."""
    s = config.shrinkage
    values = {
        "cfg_sl_pct": config.service_level_pct,
        "cfg_sl_sec": config.service_level_seconds,
        "cfg_occ": config.max_occupancy_pct,
        "cfg_asa_on": config.max_asa_seconds is not None,
        "cfg_asa": config.max_asa_seconds if config.max_asa_seconds is not None else _KEYS["cfg_asa"],
        "cfg_pat_on": config.mean_patience_seconds is not None,
        "cfg_pat": config.mean_patience_seconds if config.mean_patience_seconds is not None else _KEYS["cfg_pat"],
        "cfg_aht": config.aht_seconds,
        "cfg_shr_pauses": s.pauses_pct,
        "cfg_shr_training": s.training_pct,
        "cfg_shr_absent": s.absenteeism_pct,
        "cfg_shr_vacation": s.vacation_pct,
        "cfg_shr_other": s.other_pct,
        "cfg_cost_on": config.cost_per_hour is not None,
        "cfg_cost": config.cost_per_hour if config.cost_per_hour is not None else _KEYS["cfg_cost"],
        "cfg_shift": config.shift_hours,
    }
    st.session_state.update(values)


def _apply_preset() -> None:
    name = st.session_state.get("cfg_preset")
    if name in PRESETS:
        _config_to_state(PRESETS[name])


def config_panel(interval_minutes: int) -> StaffingConfig | None:
    """Sidebar panel with every staffing parameter. Returns None (and shows why) if it is invalid."""
    for key, default in _KEYS.items():
        st.session_state.setdefault(key, default)
    with st.sidebar.expander("3. Dimensionamento (configuração)"):
        st.caption("Os valores iniciais são exemplos editáveis, não referência da sua operação.")
        st.selectbox(
            "Exemplo para começar", ["(personalizado)", *PRESETS],
            format_func=lambda n: PRESET_LABELS.get(n, n), key="cfg_preset", on_change=_apply_preset,
        )
        uploaded = st.file_uploader("Carregar configuração (JSON)", type=["json"], key="cfg_upload")
        if uploaded is not None and st.session_state.get("cfg_loaded") != uploaded.name:
            try:
                _config_to_state(StaffingConfig.from_dict(json.loads(uploaded.getvalue())))
                st.session_state["cfg_loaded"] = uploaded.name
            except (ValueError, TypeError) as exc:
                st.error(f"Configuração inválida: {exc}")
        st.number_input("Meta de nível de serviço (% das chamadas)", 1.0, 100.0, key="cfg_sl_pct",
                        help="X% das chamadas atendidas em até Y segundos.")
        st.number_input("…atendidas em até (segundos)", 0.0, 3600.0, key="cfg_sl_sec")
        st.number_input("Ocupação máxima dos agentes (%)", 1.0, 100.0, key="cfg_occ",
                        help="Limite de tempo ocupado por agente; evita equipes no limite.")
        st.checkbox("Limitar a espera média (ASA)", key="cfg_asa_on")
        if st.session_state["cfg_asa_on"]:
            st.number_input("Espera média máxima (s)", 0.0, 3600.0, key="cfg_asa")
        st.checkbox("Clientes desistem da fila (Erlang A)", key="cfg_pat_on",
                    help="Desligado: o cálculo supõe que ninguém desiste (Erlang C).")
        if st.session_state["cfg_pat_on"]:
            st.number_input("Paciência média (s)", 1.0, 3600.0, key="cfg_pat")
        st.number_input("TMA padrão (s)", 1.0, 7200.0, key="cfg_aht",
                        help="Tempo médio de atendimento usado quando não há outro TMA.")
        st.markdown("**Shrinkage** (% do tempo pago sem atender)")
        st.number_input("Pausas (%)", 0.0, 99.0, key="cfg_shr_pauses")
        st.number_input("Treinamento (%)", 0.0, 99.0, key="cfg_shr_training")
        st.number_input("Absenteísmo (%)", 0.0, 99.0, key="cfg_shr_absent")
        st.number_input("Férias (%)", 0.0, 99.0, key="cfg_shr_vacation")
        st.number_input("Outros (%)", 0.0, 99.0, key="cfg_shr_other")
        st.checkbox("Calcular custo", key="cfg_cost_on")
        if st.session_state["cfg_cost_on"]:
            st.number_input("Custo por hora de uma pessoa escalada", 0.0, 100000.0, key="cfg_cost")
        st.number_input("Horas pagas por pessoa por dia", 1.0, 24.0, key="cfg_shift",
                        help="Para converter horas escaladas em pessoas (FTE).")

        if interval_minutes not in VALID_INTERVALS:
            st.warning("O dimensionamento precisa de um intervalo de 5 a 60 minutos.")
            return None
        try:
            ss = st.session_state
            config = StaffingConfig(
                interval_minutes=interval_minutes,
                service_level_pct=ss["cfg_sl_pct"],
                service_level_seconds=ss["cfg_sl_sec"],
                max_occupancy_pct=ss["cfg_occ"],
                max_asa_seconds=ss["cfg_asa"] if ss["cfg_asa_on"] else None,
                mean_patience_seconds=ss["cfg_pat"] if ss["cfg_pat_on"] else None,
                aht_seconds=ss["cfg_aht"],
                shrinkage=ShrinkageConfig(
                    ss["cfg_shr_pauses"], ss["cfg_shr_training"], ss["cfg_shr_absent"],
                    ss["cfg_shr_vacation"], ss["cfg_shr_other"],
                ),
                cost_per_hour=ss["cfg_cost"] if ss["cfg_cost_on"] else None,
                shift_hours=ss["cfg_shift"],
            )
        except ValueError as exc:
            st.error(str(exc))
            return None
        st.download_button("Salvar configuração (JSON)", json.dumps(config.to_dict(), indent=2, ensure_ascii=False),
                           file_name="configuracao_dimensionamento.json")
    return config


# --- charts and tables ---------------------------------------------------------------------------
def display_table(plan: pd.DataFrame) -> pd.DataFrame:
    """The plan with Portuguese column names and sensible rounding, for the screen and the CSV."""
    shown = plan[[c for c in DISPLAY_COLUMNS if c in plan.columns]].rename(columns=DISPLAY_COLUMNS)
    return shown.round({"TMA (s)": 0, "Carga (Erlangs)": 2, "Nível de serviço esperado (%)": 1,
                        "Espera média (s)": 1, "Ocupação (%)": 1, "Prob. de espera": 3,
                        "Abandono esperado (%)": 1, "Chamadas": 1, "Custo": 2})


def agents_figure(plan: pd.DataFrame, plan_range: pd.DataFrame | None) -> go.Figure:
    fig = go.Figure()
    if plan_range is not None:
        fig.add_scatter(x=plan_range.index, y=plan_range["agents_high"], line={"width": 0}, showlegend=False)
        fig.add_scatter(x=plan_range.index, y=plan_range["agents_low"], fill="tonexty", line={"width": 0},
                        fillcolor="rgba(31,119,180,0.2)", name="Faixa de volume 10%–90%")
    fig.add_bar(x=plan.index, y=plan["agents"], name="Agentes atendendo", marker_color="#1f77b4")
    fig.add_scatter(x=plan.index, y=plan["scheduled"], name="Pessoas escaladas", line={"color": "#d35400"})
    fig.update_layout(height=380, margin={"l": 10, "r": 10, "t": 10, "b": 10}, legend={"orientation": "h"},
                      yaxis_title="Pessoas")
    return fig


def goal_figure(plan: pd.DataFrame, column: str, goal: float, title: str, goal_name: str) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(x=plan.index, y=plan[column], name=title, line={"color": "#1f77b4"})
    fig.add_hline(y=goal, line_dash="dash", line_color="#999", annotation_text=goal_name)
    fig.update_layout(height=300, margin={"l": 10, "r": 10, "t": 10, "b": 10}, yaxis_title=title)
    return fig


def expected_service_level(plan: pd.DataFrame) -> float:
    """Whole-period service level expected by the formulas, weighting each interval by its calls."""
    total = plan["calls"].sum()
    return float((plan["service_level_pct"] * plan["calls"]).sum() / total) if total > 0 else float("nan")


# --- the tab -------------------------------------------------------------------------------------
def render_staffing_tab(
    series: pd.Series,
    freq: str,
    config: StaffingConfig | None,
    run_forecast: Callable[[int], tuple[pd.Series, pd.Series, pd.Series]],
    horizon: int,
) -> None:
    """Calls (forecast or history) + AHT + goal -> agents and people per interval, validated by simulation.

    ``run_forecast(horizon)`` returns the (point, lower, upper) forecast as series indexed by interval start.
    """
    st.write("Transforma o volume de chamadas em **quantos agentes cada intervalo precisa** para cumprir "
             "a meta de nível de serviço. Ajuste os parâmetros em *3. Dimensionamento* na barra lateral.")
    if config is None:
        st.info("Corrija a configuração na barra lateral para dimensionar.")
        return

    source = st.radio("Volume a dimensionar", ["Previsão do TimesFM", "Últimos intervalos do histórico"],
                      horizontal=True)
    history_n = None
    if source.startswith("Últimos"):
        history_n = st.slider("Quantos intervalos do histórico", 6, min(len(series), 672), min(48, len(series)))
    aht_choice = st.radio("TMA (tempo médio de atendimento)",
                          ["Constante (TMA padrão)", "Exemplo sintético (varia ao longo do dia)", "Arquivo CSV"],
                          horizontal=True)
    aht_file = None
    if aht_choice == "Arquivo CSV":
        aht_file = st.file_uploader("CSV com timestamp,aht_seconds ou weekday,hour,aht_seconds", type=["csv"],
                                    key="aht_upload")

    if st.button("Dimensionar", type="primary"):
        try:
            plan_range = None
            if history_n is None:
                point, lower, upper = run_forecast(horizon)
                calls = point
                range_inputs = (point, lower, upper)
            else:
                calls = series.iloc[-history_n:]
                range_inputs = None
            if aht_choice.startswith("Constante"):
                aht = ConstantAHT(config.aht_seconds)
            elif aht_choice.startswith("Exemplo"):
                aht = SeriesAHT(synthetic_aht(calls.index, config.aht_seconds), config.aht_seconds)
            elif aht_file is not None:
                aht = load_aht_csv(aht_file, config.aht_seconds)
            else:
                st.warning("Envie o arquivo de TMA ou escolha outra opção.")
                return
            plan = build_plan(calls, config, aht)
            if range_inputs is not None:
                plan_range = build_plan_range(*range_inputs, config, aht)
        except ValueError as exc:
            st.error(str(exc))
            return
        st.session_state["staffing"] = {"plan": plan, "range": plan_range, "config": config}
        st.session_state.pop("staffing_validation", None)

    saved = st.session_state.get("staffing")
    if not saved:
        return
    plan, plan_range, used = saved["plan"], saved["range"], saved["config"]
    st.caption("Resultado com a configuração do momento em que você clicou em *Dimensionar*.")

    peak = plan["agents"].max()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pico de agentes", f"{peak:.0f}")
    c2.metric("Pico de pessoas escaladas", f"{plan['scheduled'].max():.0f}")
    c3.metric("Nível de serviço esperado", f"{expected_service_level(plan):.1f}%")
    total_cost = plan["cost"].sum() if "cost" in plan else None
    c4.metric("Custo no período", f"{total_cost:,.0f}" if total_cost is not None else "n/d")

    st.plotly_chart(agents_figure(plan, plan_range), width="stretch")
    if plan_range is not None:
        st.caption("A faixa azul mostra os agentes necessários se o volume vier no cenário baixo (10%) ou alto (90%) "
                   f"da previsão: de {plan_range['agents_low'].max():.0f} a {plan_range['agents_high'].max():.0f} no pico.")
    left, right = st.columns(2)
    left.plotly_chart(goal_figure(plan, "service_level_pct", used.service_level_pct,
                                  "Nível de serviço esperado (%)", "meta"), width="stretch")
    right.plotly_chart(goal_figure(plan, "occupancy_pct", used.max_occupancy_pct,
                                   "Ocupação (%)", "teto"), width="stretch")

    st.subheader("Por intervalo")
    table = display_table(plan)
    st.dataframe(table, width="stretch")
    st.download_button("Baixar o dimensionamento (CSV)", table.rename_axis("timestamp").to_csv().encode(),
                       file_name="dimensionamento.csv")

    st.subheader("Por dia")
    daily = daily_summary(plan, used.interval_minutes, used.shift_hours).rename(columns={
        "agent_hours": "Horas de agente", "scheduled_hours": "Horas escaladas", "peak_agents": "Pico de agentes",
        "peak_scheduled": "Pico de pessoas escaladas", "fte": "FTE"}).round(1)
    daily.index = daily.index.strftime("%Y-%m-%d")
    st.dataframe(daily, width="stretch")

    st.subheader("Validar no simulador")
    st.write("Simula a central com essa equipe e confere o nível de serviço de verdade, com chamadas chegando "
             "ao acaso. Se o simulador ficar bem abaixo da meta, o cálculo está otimista para o seu caso.")
    reps = st.slider("Repetições da simulação", 3, 30, 10)
    if st.button("Validar no simulador"):
        with st.spinner("Simulando..."):
            result = simulate_replications(
                plan["calls"].to_numpy(), plan["agents"].to_numpy(), plan["aht_seconds"].to_numpy(),
                used.interval_minutes, n_replications=reps, seed=0,
                mean_patience_seconds=used.mean_patience_seconds,
                service_level_seconds=used.service_level_seconds,
            )
        st.session_state["staffing_validation"] = result
    validation = st.session_state.get("staffing_validation")
    if validation is not None:
        sl, sl_ci = validation.overall["service_level_pct"]
        ab, ab_ci = validation.overall["abandon_pct"]
        wt, wt_ci = validation.overall["avg_wait_answered_seconds"]
        oc, oc_ci = validation.overall["occupancy_pct"]
        v1, v2, v3, v4 = st.columns(4)
        v1.metric("Nível de serviço simulado", f"{sl:.1f}% ± {sl_ci:.1f}",
                  delta=f"{sl - used.service_level_pct:+.1f} p.p. da meta")
        v2.metric("Abandono simulado", f"{ab:.1f}% ± {ab_ci:.1f}")
        v3.metric("Espera média (atendidas)", f"{wt:.0f} s ± {wt_ci:.0f}")
        v4.metric("Ocupação simulada", f"{oc:.0f}% ± {oc_ci:.0f}")
        sim = validation.intervals
        fig = go.Figure()
        fig.add_scatter(x=plan.index, y=plan["service_level_pct"], name="Esperado (fórmula)", line={"color": "#999"})
        fig.add_scatter(x=plan.index, y=sim["service_level_pct"], name="Simulado (média)", line={"color": "#1f77b4"},
                        error_y={"type": "data", "array": sim["service_level_pct_ci"].fillna(0), "visible": True})
        fig.add_hline(y=used.service_level_pct, line_dash="dash", line_color="#d35400", annotation_text="meta")
        fig.update_layout(height=320, margin={"l": 10, "r": 10, "t": 10, "b": 10}, legend={"orientation": "h"},
                          yaxis_title="Nível de serviço (%)")
        st.plotly_chart(fig, width="stretch")
        st.caption(f"Média de {validation.n_replications} simulações, com intervalo de confiança de 95% (±). "
                   "O simulador começa com a central vazia, então os primeiros intervalos do período saem melhores.")
