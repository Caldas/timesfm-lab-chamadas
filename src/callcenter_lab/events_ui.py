"""Streamlit pieces for the event calendar (holidays, campaigns): the sidebar panel and the with/without comparison."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .backtest import BacktestResult
from .events import load_events


def events_panel(data_dir: Path) -> pd.DataFrame | None:
    """Sidebar section to load an event calendar (upload or an example). Returns the events or None."""
    with st.sidebar.expander("4. Eventos: feriados e campanhas (opcional)"):
        st.caption("Informe feriados, campanhas ou incidentes (CSV com `data`, `tipo`, `efeito`, `fim`, `nome`). "
                   "O modelo recebe esses dias como entrada extra e pode usá-los na previsão.")
        upload = st.file_uploader("Calendário de eventos (CSV)", type=["csv"], key="events_upload")
        examples = {p.name: p for p in sorted((data_dir / "samples" / "eventos").glob("*.csv"))}
        choice = "(nenhum)"
        if upload is None and examples:
            choice = st.selectbox("…ou um exemplo", ["(nenhum)", *examples], key="events_choice")
        source = upload if upload is not None else examples.get(choice)
        if source is None:
            return None
        try:
            events = load_events(source if upload is not None else str(source))
        except (ValueError, pd.errors.ParserError) as exc:
            st.error(f"Não consegui ler o calendário: {exc}")
            return None
        shown = events.assign(
            start=events["start"].dt.strftime("%Y-%m-%d"), end=events["end"].dt.strftime("%Y-%m-%d")
        ).rename(columns={"start": "início", "end": "fim", "kind": "tipo", "effect": "efeito", "name": "nome"})
        st.dataframe(shown, hide_index=True, width="stretch")
        return events


MODE_LABELS = {
    "adjust": "Ajuste pelo efeito informado",
    "covariates": "Covariáveis do modelo",
    "none": "Não usar os eventos",
}


def mode_selector(events: pd.DataFrame | None) -> str:
    """Radio that says how the event calendar is used in the forecast: ``adjust``, ``covariates`` or ``none``."""
    if events is None:
        return "none"
    choice = st.radio(
        "Como usar os eventos na previsão", list(MODE_LABELS.values()), key="events_mode", horizontal=True,
        help="Ajuste: o modelo prevê o volume normal e o efeito informado de cada evento é reaplicado (o histórico "
             "também é corrigido). Covariáveis: o modelo recebe os eventos como entrada extra e decide sozinho.",
    )
    mode = next(key for key, label in MODE_LABELS.items() if label == choice)
    if mode == "adjust" and events["effect"].isna().all():
        st.caption("Nenhum evento tem *efeito* informado: o ajuste não muda a previsão. Informe o efeito "
                   "(ex.: 1.5) ou use covariáveis.")
    return mode


def render_comparison(plain: BacktestResult, with_covariates: BacktestResult, adjusted: BacktestResult,
                      kinds: list[str]) -> None:
    """Table and chart: the same reality check with no events, with covariates and with the declared-effect adjustment."""
    def row(label: str, bt: BacktestResult) -> dict:
        return {"Previsão": label, "WAPE (%)": bt.wape, "Viés (%)": bt.bias_pct, "MAE (chamadas)": bt.mae,
                "Dentro da faixa 10–90% (%)": 100 * bt.coverage}

    table = pd.DataFrame([
        row("Sem eventos", plain), row("Covariáveis do modelo", with_covariates),
        row("Ajuste pelo efeito informado", adjusted),
    ]).round(1)
    st.subheader("Com e sem eventos")
    st.caption(f"Tipos de evento: {', '.join(kinds)}. O ajuste só vale tanto quanto o efeito que você informou.")
    st.dataframe(table, hide_index=True, width="stretch")
    if pd.isna(plain.wape):
        st.info("O trecho escondido não tem chamadas: não dá para comparar.")
    else:
        for label, bt in (("As covariáveis do modelo", with_covariates), ("O ajuste pelo efeito informado", adjusted)):
            gain = plain.wape - bt.wape
            if gain > 0.5:
                st.success(f"{label} **melhoraram** o WAPE em {gain:.1f} ponto(s) percentual(is) neste teste.")
            elif gain < -0.5:
                st.warning(f"{label} **pioraram** o WAPE em {-gain:.1f} ponto(s) percentual(is) neste teste.")
            else:
                st.info(f"{label} **não mudaram** o WAPE neste teste (diferença de {gain:+.1f} p.p.).")
    fig = go.Figure()
    tail = plain.history.iloc[-len(plain.actual) * 2:]
    fig.add_scatter(x=tail.index, y=tail.values, name="Histórico", line={"color": "#999"})
    fig.add_scatter(x=plain.actual.index, y=plain.actual.values, name="Real", line={"color": "#000"})
    fig.add_scatter(x=plain.point.index, y=plain.point.values, name="Sem eventos", line={"color": "#1f77b4"})
    fig.add_scatter(x=with_covariates.point.index, y=with_covariates.point.values, name="Covariáveis",
                    line={"color": "#2ca02c", "dash": "dot"})
    fig.add_scatter(x=adjusted.point.index, y=adjusted.point.values, name="Ajuste pelo efeito",
                    line={"color": "#d35400"})
    fig.update_layout(height=380, margin={"l": 10, "r": 10, "t": 10, "b": 10}, legend={"orientation": "h"},
                      yaxis_title="Chamadas")
    st.plotly_chart(fig, width="stretch")
