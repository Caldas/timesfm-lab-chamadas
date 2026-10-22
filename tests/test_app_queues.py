"""The optional "Filas e habilidades" tab of the Streamlit app, with a stand-in for the TimesFM model."""

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
    def predict(self, history, horizon, return_quantiles, make_positive, **kwargs):
        point = np.resize(np.asarray(history)[-336:], horizon).astype(float)
        return SimpleNamespace(forecast=point, quantiles=np.stack([point * (0.8 + 0.05 * i) for i in range(9)], axis=1))


@pytest.fixture
def app(monkeypatch):
    st.cache_resource.clear()
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr(model_module, "load_forecaster", lambda backend="auto", **kwargs: FakeModel())
    return AppTest.from_file(APP, default_timeout=180).run()


def choose_file(at, name):
    box = next(s for s in at.selectbox if s.label.endswith("escolher um arquivo"))
    box.select_index(next(i for i, option in enumerate(box.options) if option.endswith(name)))
    at.run()
    assert not at.exception, at.exception


def click(at, label):
    next(b for b in at.button if b.label == label).click()
    at.run()
    assert not at.exception, at.exception


def activate(at):
    at.checkbox(key="queues_on").set_value(True)
    at.run()
    assert not at.exception, at.exception


def test_the_tab_is_off_until_activated(app):
    assert app.checkbox(key="queues_on").value is False
    assert not [b for b in app.button if b.label == "Dimensionar cada fila"]


def test_a_single_queue_file_is_explained(app):
    activate(app)
    assert any("não tem uma coluna de fila" in i.value for i in app.info)


def test_a_file_with_queues_warns_that_values_are_averaged_without_a_filter(app):
    choose_file(app, "chamadas_sinteticas_filas.csv")
    assert any("várias filas" in i.value and "média" in i.value for i in app.info)


def test_each_queue_is_sized_on_its_own(app):
    choose_file(app, "chamadas_sinteticas_filas.csv")
    activate(app)
    click(app, "Dimensionar cada fila")
    assert not app.error
    plans, names = app.session_state["queue_plans"]
    assert names == ["vendas", "suporte", "cobrança"]
    summary = plans.summary()
    assert list(summary.index) == ["vendas", "suporte", "cobrança", "Total"]
    assert summary.loc["Total", "agent_hours"] == pytest.approx(summary.loc[names, "agent_hours"].sum())


def test_the_forecast_can_be_the_source_for_every_queue(app):
    choose_file(app, "chamadas_sinteticas_filas.csv")
    activate(app)
    next(r for r in app.radio if r.label == "Volume a dimensionar" and "Previsão do TimesFM" in r.options).set_value("Previsão do TimesFM")
    app.run()
    click(app, "Dimensionar cada fila")
    assert not app.error
    plans, _ = app.session_state["queue_plans"]
    assert len(plans.total) == 48  # the default horizon


def test_comparing_separate_and_cross_trained_teams(app):
    choose_file(app, "chamadas_sinteticas_filas.csv")
    activate(app)
    click(app, "Comparar equipes separadas × cruzada")
    assert not app.error
    comparison = app.session_state["pooling"]
    assert list(comparison.summary.index) == ["Equipes separadas", "Equipe cruzada"]
    assert comparison.summary.loc["Equipe cruzada", "agent_hours"] <= comparison.summary.loc["Equipes separadas", "agent_hours"]
    assert comparison.separate.n_replications == 10
