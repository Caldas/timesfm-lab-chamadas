"""The roster and scenarios tabs of the Streamlit app, end to end, with a stand-in for the TimesFM model."""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

pytest.importorskip("streamlit")
pytest.importorskip("scipy")
import streamlit as st
from streamlit.testing.v1 import AppTest

import callcenter_lab
import callcenter_lab.model as model_module

ROOT = Path(__file__).resolve().parent.parent
APP = str(Path(callcenter_lab.__file__).with_name("app.py"))


class FakeModel:
    def predict(self, history, horizon, return_quantiles, make_positive):
        point = np.resize(history[-48:], horizon).astype(float)
        quantiles = np.stack([point * (0.8 + 0.05 * i) for i in range(9)], axis=1)
        return SimpleNamespace(forecast=point, quantiles=quantiles)


@pytest.fixture
def app(monkeypatch):
    st.cache_resource.clear()
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr(model_module, "load_forecaster", lambda backend="auto", **kwargs: FakeModel())
    return AppTest.from_file(APP, default_timeout=120).run()


def button(at, label):
    return next(b for b in at.button if b.label == label)


def click(at, label):
    button(at, label).click()
    at.run()
    assert not at.exception, at.exception


def size_from_forecast(at):
    click(at, "Dimensionar")  # default source: the TimesFM forecast (48 intervals)
    assert at.session_state["staffing"]["range"] is not None


def size_from_history(at):
    next(r for r in at.radio if r.label == "Volume a dimensionar").set_value("Últimos intervalos do histórico")
    at.run()
    click(at, "Dimensionar")


def metric_labels(at):
    return [m.label for m in at.metric]


def test_default_interval_is_30_minutes(app):
    # The sample data is 30 min; the default once drifted to 15 min when options were added to the list.
    assert next(s for s in app.selectbox if s.label == "Intervalo").value == "30 minutos"


def test_app_has_the_five_tabs(app):
    assert [t.label for t in app.tabs] == ["🔮 Previsão", "🧪 Teste de realidade", "👥 Dimensionamento", "📅 Escala", "🧮 Cenários"]


def test_roster_and_scenarios_ask_for_the_sizing_first(app):
    infos = [i.value for i in app.info]
    assert sum("Dimensione primeiro" in text for text in infos) == 2


def test_generate_a_roster_from_the_sizing(app):
    size_from_history(app)  # the last 48 intervals of the sample are a Saturday, which has a template
    click(app, "Gerar escala")
    assert not app.error
    roster = app.session_state["roster"]
    assert len(roster.shifts) > 0 and roster.headcount >= 1
    assert {"Pessoas necessárias", "Custo da escala", "Intervalos com falta"} <= set(metric_labels(app))


def test_validate_the_roster_in_the_simulator(app):
    size_from_history(app)
    click(app, "Gerar escala")
    click(app, "Validar a escala no simulador")
    assert "Nível de serviço simulado" in metric_labels(app)
    assert app.session_state["roster_validation"].n_replications == 10


def test_compare_scenarios(app):
    size_from_forecast(app)
    click(app, "Comparar cenários")
    assert not app.error
    results = app.session_state["scenario_results"]
    assert results["scenario"].iloc[0] == "Base" and len(results) == 7
    assert "roster_shortfall_person_hours" not in results.columns  # no roster yet
    assert results["agent_hours"].iloc[0] >= 0


def test_shifts_missing_for_a_weekday_are_reported_as_shortfall(app):
    size_from_forecast(app)  # the forecast starts on a Sunday; the example shifts are only offered Mon-Sat
    click(app, "Gerar escala")
    assert any("não cobrem toda a necessidade" in w.value for w in app.warning)
    assert app.session_state["roster"].summary()["shortfall_intervals"] > 0


def test_a_closed_period_gives_an_explained_empty_roster(monkeypatch):
    class ClosedModel:
        def predict(self, history, horizon, return_quantiles, make_positive):
            zeros = np.zeros(horizon)
            return SimpleNamespace(forecast=zeros, quantiles=np.stack([zeros] * 9, axis=1))

    st.cache_resource.clear()
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr(model_module, "load_forecaster", lambda backend="auto", **kwargs: ClosedModel())
    at = AppTest.from_file(APP, default_timeout=120).run()
    click(at, "Dimensionar")
    click(at, "Gerar escala")
    assert any("Não há necessidade" in i.value for i in at.info)
    assert at.session_state["roster"].shifts.empty


def test_low_and_high_scenarios_need_the_forecast(app):
    size_from_history(app)
    click(app, "Comparar cenários")
    assert any("previsão" in e.value for e in app.error)


def test_sensitivity_analysis(app):
    size_from_forecast(app)
    next(s for s in app.selectbox if s.label == "Parâmetro").select("aht_factor")
    app.run()
    click(app, "Calcular sensibilidade")
    result = app.session_state["sensitivity_results"]
    assert len(result) == 5 and result["agent_hours"].is_monotonic_increasing


def test_a_new_sizing_clears_the_results_that_depended_on_the_old_one(app):
    size_from_forecast(app)
    click(app, "Gerar escala")
    click(app, "Comparar cenários")
    assert "roster" in app.session_state and "scenario_results" in app.session_state
    click(app, "Dimensionar")
    assert "roster" not in app.session_state and "scenario_results" not in app.session_state
