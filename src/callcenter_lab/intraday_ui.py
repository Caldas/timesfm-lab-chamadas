"""Streamlit tab "Acompanhamento do dia": planned vs actual, alerts, re-forecast and projected total."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .intraday import DayFollowUp, follow_up_day, intervals_per_day

POSITION_LABELS = {"acima": "acima da faixa", "abaixo": "abaixo da faixa", "dentro": "dentro da faixa"}


def followup_figure(result: DayFollowUp) -> go.Figure:
    fig = go.Figure()
    plan = result.plan
    fig.add_scatter(x=plan.index, y=plan["upper"], line={"width": 0}, showlegend=False)
    fig.add_scatter(x=plan.index, y=plan["lower"], fill="tonexty", line={"width": 0},
                    fillcolor="rgba(31,119,180,0.15)", name="Faixa 10%–90% do plano")
    fig.add_scatter(x=plan.index, y=plan["point"], name="Plano da manhã", line={"color": "#1f77b4"})
    fig.add_scatter(x=result.observed.index, y=result.observed.values, name="Realizado", line={"color": "#000", "width": 3})
    if result.reforecast is not None:
        fig.add_scatter(x=result.reforecast.index, y=result.reforecast["point"], name="Re-previsão",
                        line={"color": "#d35400", "width": 3})
    if result.actual_remaining is not None:
        fig.add_scatter(x=result.actual_remaining.index, y=result.actual_remaining.values,
                        name="Realizado depois do corte", line={"color": "#000", "dash": "dot"})
    fig.add_vline(x=result.cutoff, line_dash="dash", line_color="#999", annotation_text="agora")
    fig.update_layout(height=420, margin={"l": 10, "r": 10, "t": 10, "b": 10}, legend={"orientation": "h"},
                      yaxis_title="Chamadas")
    return fig


def render_followup_tab(
    series: pd.Series, freq: str, get_model: Callable, events: pd.DataFrame | None, event_mode: str
) -> None:
    st.write("Compara o **plano da manhã** com as chamadas que estão chegando, avisa quando o dia sai da faixa "
             "prevista e **re-prevê o resto do dia** com o que já aconteceu. Com dados de um dia passado, você "
             "escolhe o horário e vê se re-prever teria ajudado.")
    step = pd.Timedelta(pd.tseries.frequencies.to_offset(freq))
    per_day = intervals_per_day(freq)
    days = sorted({ts.normalize() for ts in series.index})
    if len(days) < 2:
        st.info("São necessários pelo menos dois dias de dados: um de histórico e o dia a acompanhar.")
        return
    day = st.selectbox("Dia a acompanhar", days[1:], index=len(days) - 2, format_func=lambda d: f"{d:%Y-%m-%d}")

    live = series.index[-1].normalize() == day and series.index[-1] + step < day + pd.Timedelta(days=1)
    if live:
        cutoff = series.index[-1] + step
        st.caption(f"Os dados terminam às {series.index[-1]:%H:%M}: o dia está em andamento e o corte é {cutoff:%H:%M}.")
    else:
        # options are "how many intervals of the day are already known" (1..per_day); shown as clock times
        known = st.select_slider(
            "Já temos os dados até (o resto do dia é a incógnita)", options=list(range(1, per_day + 1)), value=per_day // 2,
            format_func=lambda k: "fim do dia" if k == per_day else f"{day + step * k:%H:%M}",
        )
        cutoff = day + step * known

    c1, c2, c3 = st.columns(3)
    warn = c1.number_input("Atenção a partir de (% de desvio no dia)", 1.0, 100.0, 10.0)
    critical = c2.number_input("Crítico a partir de (%)", 1.0, 200.0, 20.0)
    consecutive = c3.slider("Intervalos seguidos fora da faixa para alertar", 1, 12, 3)

    if st.button("Acompanhar o dia", type="primary"):
        try:
            with st.spinner("Calculando o plano e a re-previsão..."):
                result = follow_up_day(get_model(), series, day, cutoff, freq, events, event_mode,
                                       warn_pct=warn, critical_pct=critical, consecutive=consecutive)
        except ValueError as exc:
            st.error(str(exc))
            return
        st.session_state["followup"] = result

    result: DayFollowUp | None = st.session_state.get("followup")
    if result is None:
        return
    s = result.summary
    if s["intervals_observed"] == 0:
        st.info("Ainda não há intervalos observados antes do horário de corte: escolha um horário mais tarde.")
    else:
        message = (f"O realizado está {s['deviation_pct']:+.1f}% em relação ao plano até agora "
                   f"({s['actual_so_far']:,.0f} chamadas contra {s['planned_so_far']:,.0f} planejadas).")
        {"ok": st.success, "atenção": st.warning, "crítico": st.error}[s["alert"]](
            f"**{s['alert'].capitalize()}.** " + message if s["alert"] != "ok" else "**Dentro do esperado.** " + message)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Desvio acumulado", "n/d" if pd.isna(s["deviation_pct"]) else f"{s['deviation_pct']:+.1f}%")
    m2.metric("Intervalos acima / abaixo da faixa", f"{s['intervals_above']} / {s['intervals_below']}")
    m3.metric("Total planejado no dia", f"{s['plan_total']:,.0f}")
    if "projected_total" in s:
        m4.metric("Projeção do dia", f"{s['projected_total']:,.0f}",
                  delta=None if pd.isna(s["projected_difference_pct"]) else f"{s['projected_difference_pct']:+.1f}% do plano",
                  delta_color="off")
    st.plotly_chart(followup_figure(result), width="stretch")

    if "plan_wape_remaining" in s:
        better = s["reforecast_wape_remaining"] < s["plan_wape_remaining"]
        st.info(
            f"**Do corte até o fim do dia**, comparando com o que de fato aconteceu: o plano da manhã teve WAPE de "
            f"{s['plan_wape_remaining']:.1f}% (viés {s['plan_bias_remaining']:+.1f}%) e a re-previsão, "
            f"{s['reforecast_wape_remaining']:.1f}% (viés {s['reforecast_bias_remaining']:+.1f}%). "
            f"Neste dia, re-prever **{'ajudou' if better else 'não ajudou'}**."
        )

    st.subheader("Desvios que se sustentam")
    if result.alerts.empty:
        st.write("Nenhum trecho com intervalos seguidos fora da faixa.")
    else:
        alerts = result.alerts.assign(
            start=result.alerts["start"].dt.strftime("%H:%M"), end=result.alerts["end"].dt.strftime("%H:%M"),
            position=result.alerts["position"].map(POSITION_LABELS),
        ).rename(columns={"start": "De", "end": "Até", "intervals": "Intervalos", "position": "Posição",
                          "planned": "Planejado", "actual": "Realizado", "difference_pct": "Diferença (%)"}).round(1)
        st.dataframe(alerts, hide_index=True, width="stretch")

    comparison = result.comparison.rename(columns={
        "point": "Plano", "lower": "Faixa baixa (10%)", "upper": "Faixa alta (90%)", "actual": "Realizado",
        "difference": "Diferença", "difference_pct": "Diferença (%)", "position": "Posição"}).round(1)
    with st.expander("Previsto × realizado por intervalo"):
        st.dataframe(comparison, width="stretch")
    st.download_button("Baixar previsto × realizado (CSV)", comparison.rename_axis("timestamp").to_csv().encode(),
                       file_name="acompanhamento_do_dia.csv")
