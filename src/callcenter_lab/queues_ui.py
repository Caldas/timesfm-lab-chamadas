"""Streamlit tab "Filas e habilidades" (optional, off by default): size each queue and compare team designs."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .events import forecast_with_events
from .loading import detect_queue_column, split_by_queue
from .synthetic import QUEUE_AHT_SECONDS
from .wfm import StaffingConfig, build_queue_plans, compare_pooling


def _queue_candidates(df: pd.DataFrame, date_col: str, value_col: str) -> list[str]:
    return [c for c in df.columns if c not in (date_col, value_col) and not pd.api.types.is_numeric_dtype(df[c])
            and 2 <= df[c].nunique() <= 20]


def agents_by_queue_figure(total: pd.DataFrame, names: list[str]) -> go.Figure:
    fig = go.Figure()
    for name in names:
        fig.add_bar(x=total.index, y=total[f"agents_{name}"], name=name)
    fig.update_layout(barmode="stack", height=360, margin={"l": 10, "r": 10, "t": 10, "b": 10},
                      legend={"orientation": "h"}, yaxis_title="Agentes")
    return fig


def render_queues_tab(
    raw_df: pd.DataFrame, date_col: str, value_col: str, freq: str, how: str, fill: str, config: StaffingConfig | None,
    max_history: int, horizon: int, get_model: Callable, events: pd.DataFrame | None, event_mode: str,
) -> None:
    st.write("Para centrais com **várias filas** (vendas, suporte, cobrança...). Por padrão, cada fila é "
             "dimensionada **sozinha**, como se tivesse a sua própria equipe. Aqui você também pode **comparar** isso "
             "com uma **equipe cruzada**, em que os mesmos agentes atendem todas as filas, medindo a diferença "
             "pelo simulador. Este recurso é opcional e fica desligado até você ativá-lo.")
    if not st.checkbox("Ativar filas e habilidades", key="queues_on"):
        st.caption("Use um arquivo com uma coluna de fila (por exemplo, `chamadas_sinteticas_filas.csv`, em "
                   "`data/samples`). O guia explica quando o Erlang C de uma fila só não serve.")
        return
    if config is None:
        st.info("Corrija a configuração do dimensionamento na barra lateral (intervalo de 5 a 60 minutos).")
        return
    candidates = _queue_candidates(raw_df, date_col, value_col)
    if not candidates:
        st.info("O arquivo carregado não tem uma coluna de fila (texto com 2 a 20 valores diferentes). "
                "Escolha, em *1. Dados*, um arquivo com filas, como `chamadas_sinteticas_filas.csv`.")
        return
    guess = detect_queue_column(raw_df, date_col, value_col)
    queue_col = st.selectbox("Coluna que identifica a fila", candidates, index=candidates.index(guess) if guess in candidates else 0)
    try:
        by_queue = {name: s.iloc[-max_history:] for name, s in split_by_queue(raw_df, date_col, value_col, queue_col, freq, how, fill).items()}
    except ValueError as exc:
        st.error(str(exc))
        return
    names = list(by_queue)
    st.caption(f"{len(names)} filas encontradas: {', '.join(names)}.")

    st.subheader("TMA de cada fila")
    key = "queue_aht_table:" + "|".join(names)
    st.session_state.setdefault(key, pd.DataFrame({
        "fila": names, "TMA (s)": [float(QUEUE_AHT_SECONDS.get(n, config.aht_seconds)) for n in names]}))
    edited = st.data_editor(st.session_state[key], key=key + ":editor", hide_index=True, width="stretch",
                            disabled=["fila"], column_config={"TMA (s)": st.column_config.NumberColumn(min_value=1.0)})
    aht = {row["fila"]: float(row["TMA (s)"]) for _, row in edited.iterrows() if pd.notna(row["TMA (s)"]) and row["TMA (s)"] > 0}
    if set(aht) != set(names):
        st.warning("Informe um TMA maior que zero para todas as filas.")
        return

    source = st.radio("Volume a dimensionar", ["Últimos intervalos do histórico", "Previsão do TimesFM"], horizontal=True, key="queues_source")
    history_n = None
    if source.startswith("Últimos"):
        length = len(next(iter(by_queue.values())))
        history_n = st.slider("Quantos intervalos do histórico", 6, min(length, 672), min(48, length), key="queues_history")

    def volumes() -> dict[str, pd.Series]:
        if history_n is not None:
            return {n: s.iloc[-history_n:] for n, s in by_queue.items()}
        model = get_model()
        out = {}
        for name, series in by_queue.items():
            result = forecast_with_events(model, series, horizon, freq, events, event_mode)
            out[name] = pd.Series(result.point, index=pd.date_range(series.index[-1], periods=horizon + 1, freq=freq)[1:])
        return out

    c1, c2 = st.columns(2)
    if c1.button("Dimensionar cada fila", type="primary"):
        try:
            with st.spinner("Calculando..."):
                calls = volumes()
                st.session_state["queue_plans"] = (build_queue_plans(calls, config, aht), names)
                st.session_state["queue_calls"] = calls
        except ValueError as exc:
            st.error(str(exc))
            return
        st.session_state.pop("pooling", None)
    reps = st.slider("Repetições da simulação", 3, 30, 10, key="queues_reps")
    if c2.button("Comparar equipes separadas × cruzada"):
        try:
            with st.spinner("Dimensionando e simulando as duas equipes..."):
                calls = volumes()
                st.session_state["queue_calls"] = calls
                st.session_state["queue_plans"] = (build_queue_plans(calls, config, aht), names)
                st.session_state["pooling"] = compare_pooling(calls, config, aht, n_replications=reps)
        except ValueError as exc:
            st.error(str(exc))
            return

    saved = st.session_state.get("queue_plans")
    if saved is None:
        return
    plans, plan_names = saved
    st.subheader("Cada fila com a sua equipe")
    summary = plans.summary().rename(columns={
        "calls": "Chamadas", "peak_agents": "Pico de agentes", "agent_hours": "Horas de agente",
        "peak_scheduled": "Pico de pessoas escaladas", "scheduled_hours": "Horas escaladas"}).round(1)
    st.dataframe(summary, width="stretch")
    st.plotly_chart(agents_by_queue_figure(plans.total, plan_names), width="stretch")
    st.download_button("Baixar o dimensionamento por fila (CSV)", plans.total.rename_axis("timestamp").to_csv().encode(),
                       file_name="dimensionamento_por_fila.csv")

    comparison = st.session_state.get("pooling")
    if comparison is None:
        return
    st.subheader("Equipes separadas × equipe cruzada")
    table = comparison.summary.rename(columns={
        "peak_agents": "Pico de agentes", "agent_hours": "Horas de agente", "scheduled_hours": "Horas escaladas",
        "min_service_level_pct": "Pior nível de serviço (%)", "avg_service_level_pct": "Nível de serviço médio (%)",
        "avg_abandon_pct": "Abandono médio (%)", "agent_hours_vs_separate_pct": "Horas de agente vs. separadas (%)"}).round(1)
    st.dataframe(table, width="stretch")
    saving = comparison.summary.loc["Equipe cruzada", "agent_hours_vs_separate_pct"]
    if saving < -0.5:
        st.success(f"A equipe cruzada precisa de **{-saving:.0f}% menos horas de agente** para a mesma meta, segundo o "
                   "simulador. O custo é treinar os agentes em várias filas.")
    else:
        st.info("Neste volume, a equipe cruzada não reduz as horas de agente de forma relevante.")
    per_queue = comparison.per_queue.rename(columns={
        "design": "Equipe", "queue": "Fila", "service_level_pct": "Nível de serviço (%)", "service_level_ci": "± (95%)",
        "abandon_pct": "Abandono (%)", "avg_wait_answered_seconds": "Espera média (s)"}).round(1)
    st.dataframe(per_queue, hide_index=True, width="stretch")
    fig = go.Figure()
    for design in comparison.agents.columns:
        fig.add_scatter(x=comparison.agents.index, y=comparison.agents[design], name=design, line={"shape": "hv"})
    fig.update_layout(height=320, margin={"l": 10, "r": 10, "t": 10, "b": 10}, legend={"orientation": "h"}, yaxis_title="Agentes")
    st.plotly_chart(fig, width="stretch")
    st.caption("Médias de várias simulações. As duas equipes são dimensionadas para a mesma meta; o simulador mostra o "
               "que cada uma realmente entrega.")
