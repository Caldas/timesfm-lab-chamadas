"""Streamlit tab "Cenários": compare what-if scenarios side by side and vary one parameter at a time."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from .staffing_ui import excel_download
from .wfm import SENSITIVITY_PARAMETERS, example_scenarios, run_scenarios, sensitivity
from .wfm.scenarios import SCENARIO_COLUMNS, scenarios_from_table, scenarios_to_table
from .wfm.tables import scenarios_result_table, sensitivity_result_table


def render_scenarios_tab() -> None:
    st.write("Responde a perguntas **“e se...”**: e se o volume vier no cenário alto da previsão? E se o TMA subir "
             "10%? E se o absenteísmo aumentar? Cada cenário refaz o dimensionamento e compara com o primeiro.")
    saved = st.session_state.get("staffing")
    if not saved:
        st.info("Dimensione primeiro: use a aba Dimensionamento e clique em *Dimensionar*.")
        return
    config, volumes, aht = saved["config"], saved["volumes"], saved["aht"]
    if "low" not in volumes:
        st.caption("Os cenários de volume *baixo* e *alto* só existem quando o dimensionamento usa a previsão do TimesFM.")

    st.subheader("Cenários")
    st.caption("A primeira linha é a referência. Deixe uma célula em branco para manter o valor da configuração. "
               "*shrinkage_pp* soma pontos percentuais ao shrinkage total.")
    st.session_state.setdefault("scenario_table", scenarios_to_table(example_scenarios()))
    edited = st.data_editor(
        st.session_state["scenario_table"], num_rows="dynamic", key="scenario_editor", width="stretch",
        column_config={"volume": st.column_config.SelectboxColumn("volume", options=["baixo", "esperado", "alto"])},
    )
    roster = st.session_state.get("roster")
    if roster is not None:
        st.caption("Há uma escala gerada: a tabela também mostra como ela cobriria cada cenário.")

    if st.button("Comparar cenários", type="primary"):
        try:
            scenarios = scenarios_from_table(edited[[c for c in SCENARIO_COLUMNS if c in edited.columns]])
            with st.spinner("Calculando..."):
                st.session_state["scenario_results"] = run_scenarios(volumes, scenarios, config, aht, roster=roster)
        except (ValueError, TypeError) as exc:
            st.error(str(exc))
            return

    results = st.session_state.get("scenario_results")
    if results is not None:
        table = scenarios_result_table(results)
        st.dataframe(table, width="stretch", hide_index=True)
        fig = go.Figure()
        fig.add_bar(x=results["scenario"], y=results["agent_hours"], name="Horas de agente", marker_color="#1f77b4")
        fig.add_bar(x=results["scenario"], y=results["scheduled_hours"], name="Horas escaladas", marker_color="#d35400")
        fig.update_layout(height=340, barmode="group", margin={"l": 10, "r": 10, "t": 10, "b": 10}, legend={"orientation": "h"})
        st.plotly_chart(fig, width="stretch")
        st.download_button("Baixar os cenários (CSV)", table.to_csv(index=False).encode(), file_name="cenarios.csv")

    st.subheader("Sensibilidade")
    st.write("Varia **um parâmetro de cada vez** em torno da configuração atual e mostra o efeito no dimensionamento.")
    parameter = st.selectbox("Parâmetro", list(SENSITIVITY_PARAMETERS), format_func=lambda k: SENSITIVITY_PARAMETERS[k][0])
    if st.button("Calcular sensibilidade"):
        try:
            with st.spinner("Calculando..."):
                result = sensitivity(volumes["expected"], config, parameter, aht=aht)
            result.attrs["parameter"] = parameter
            st.session_state["sensitivity_results"] = result
        except ValueError as exc:
            st.error(str(exc))
            return
    result = st.session_state.get("sensitivity_results")
    if result is not None:
        label = SENSITIVITY_PARAMETERS[result.attrs.get("parameter", parameter)][0]
        table = sensitivity_result_table(result)
        st.dataframe(table, width="stretch", hide_index=True)
        fig = go.Figure(go.Scatter(x=result["value"], y=result["agent_hours"], mode="lines+markers", name="Horas de agente"))
        fig.update_layout(height=300, margin={"l": 10, "r": 10, "t": 10, "b": 10}, xaxis_title=label, yaxis_title="Horas de agente")
        st.plotly_chart(fig, width="stretch")
        st.download_button("Baixar a sensibilidade (CSV)", table.to_csv(index=False).encode(), file_name="sensibilidade.csv")
    excel_download("excel_scenarios")
