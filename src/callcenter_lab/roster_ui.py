"""Streamlit tab "Escala": shift templates -> optimised roster -> coverage, checked in the simulator."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from .staffing_ui import excel_download
from .wfm import RosterRules, evaluate_roster, example_templates, optimize_roster
from .wfm.scheduling import TABLE_COLUMNS, templates_from_table, templates_to_table
from .wfm.tables import breaks_table, coverage_table, shifts_table


def coverage_figure(roster) -> go.Figure:
    cov = roster.coverage
    fig = go.Figure()
    fig.add_scatter(x=cov.index, y=cov["covered"], name="Cobertura (no turno, sem pausa)", line={"shape": "hv", "color": "#1f77b4"})
    fig.add_scatter(x=cov.index, y=cov["needed"], name="Necessidade (pessoas escaladas)", line={"shape": "hv", "color": "#d35400", "dash": "dot"})
    fig.update_layout(height=380, margin={"l": 10, "r": 10, "t": 10, "b": 10}, legend={"orientation": "h"}, yaxis_title="Pessoas")
    return fig


def render_roster_tab() -> None:
    st.write("Distribui as pessoas em **turnos** para cobrir a necessidade do dimensionamento ao menor custo, "
             "escalonando as pausas de refeição. Antes, faça o dimensionamento na aba anterior.")
    saved = st.session_state.get("staffing")
    if not saved:
        st.info("Dimensione primeiro: use a aba Dimensionamento e clique em *Dimensionar*.")
        return
    plan, config = saved["plan"], saved["config"]

    st.subheader("Turnos")
    st.caption("Edite, acrescente ou apague linhas. Início e duração precisam ser múltiplos do intervalo "
               f"({config.interval_minutes} min). Dias: seg-sex, sab, dom... A pausa de refeição é tirada da "
               "cobertura; as demais pausas continuam no shrinkage.")
    st.session_state.setdefault("roster_template_table", templates_to_table(example_templates()))
    edited = st.data_editor(
        st.session_state["roster_template_table"], num_rows="dynamic", key="roster_templates_editor", width="stretch",
        column_config={"refeição_paga": st.column_config.CheckboxColumn("refeição_paga")},
    )

    c1, c2, c3 = st.columns(3)
    max_days = c1.number_input("Máximo de dias trabalhados por semana (por pessoa)", 1, 7, 5)
    cost_default = c2.number_input("Custo por hora (turnos sem custo próprio)", 0.0, 100000.0,
                                   float(config.cost_per_hour) if config.cost_per_hour is not None else 1.0)
    time_limit = c3.slider("Tempo máximo de cálculo (s)", 5, 120, 30)
    limit_headcount = st.checkbox("Limitar o número de pessoas disponíveis")
    max_headcount = st.number_input("Pessoas disponíveis", 1, 10000, 10) if limit_headcount else None

    if st.button("Gerar escala", type="primary"):
        try:
            templates = templates_from_table(edited[[c for c in TABLE_COLUMNS if c in edited.columns]])
            rules = RosterRules(max_days_per_week=int(max_days), max_headcount=int(max_headcount) if max_headcount else None,
                                time_limit_seconds=float(time_limit), default_cost_per_hour=float(cost_default))
            with st.spinner("Otimizando a escala..."):
                roster = optimize_roster(plan["scheduled"], templates, config.interval_minutes, rules)
        except (ValueError, TypeError, RuntimeError) as exc:
            st.error(str(exc))
            return
        st.session_state["roster"] = roster
        st.session_state.pop("roster_validation", None)
        st.session_state.pop("scenario_results", None)

    roster = st.session_state.get("roster")
    if roster is None:
        return
    summary = roster.summary()
    if roster.coverage["needed"].sum() == 0:
        st.info("Não há necessidade de pessoas no período do dimensionamento (a central está fechada nesses dias?). "
                "Refaça o dimensionamento com outro período, por exemplo um horizonte maior ou dias de funcionamento.")
        return
    st.caption(f"Solução {roster.status}.")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Pessoas necessárias", f"{summary['headcount']}",
              help="Quantas pessoas a equipe precisa ter para respeitar o limite de dias por semana.")
    m2.metric("Custo da escala", f"{summary['cost']:,.0f}")
    m3.metric("Intervalos com falta", f"{summary['shortfall_intervals']}",
              delta=f"{summary['shortfall_person_hours']:.1f} h de falta" if summary["shortfall_intervals"] else None, delta_color="inverse")
    m4.metric("Horas de sobra", f"{summary['surplus_person_hours']:.1f}")
    if summary["shortfall_intervals"]:
        st.warning("Os turnos e as regras não cobrem toda a necessidade. Acrescente turnos, aumente os máximos "
                   "ou libere mais pessoas.")
    st.plotly_chart(coverage_figure(roster), width="stretch")

    st.subheader("Turnos por dia")
    shifts = shifts_table(roster)
    st.dataframe(shifts, width="stretch", hide_index=True)
    st.download_button("Baixar os turnos (CSV)", shifts.to_csv(index=False).encode(), file_name="escala_turnos.csv")
    with st.expander("Pausas de refeição"):
        breaks = breaks_table(roster)
        st.dataframe(breaks, width="stretch", hide_index=True)
        st.download_button("Baixar as pausas (CSV)", breaks.to_csv(index=False).encode(), file_name="escala_pausas.csv")
    with st.expander("Cobertura por intervalo"):
        coverage = coverage_table(roster)
        st.dataframe(coverage, width="stretch")
        st.download_button("Baixar a cobertura (CSV)", coverage.rename_axis("timestamp").to_csv().encode(),
                           file_name="escala_cobertura.csv")
    excel_download("excel_roster")

    st.subheader("Validar a escala no simulador")
    st.write("Simula a central com os agentes que essa escala realmente entrega (cobertura menos shrinkage).")
    reps = st.slider("Repetições da simulação", 3, 30, 10, key="roster_reps")
    if st.button("Validar a escala no simulador"):
        with st.spinner("Simulando..."):
            st.session_state["roster_validation"] = evaluate_roster(roster, plan, config, n_replications=reps)
    validation = st.session_state.get("roster_validation")
    if validation is not None:
        sl, sl_ci = validation.overall["service_level_pct"]
        ab, ab_ci = validation.overall["abandon_pct"]
        wt, wt_ci = validation.overall["avg_wait_answered_seconds"]
        v1, v2, v3 = st.columns(3)
        v1.metric("Nível de serviço simulado", f"{sl:.1f}% ± {sl_ci:.1f}", delta=f"{sl - config.service_level_pct:+.1f} p.p. da meta")
        v2.metric("Abandono simulado", f"{ab:.1f}% ± {ab_ci:.1f}")
        v3.metric("Espera média (atendidas)", f"{wt:.0f} s ± {wt_ci:.0f}")
