"""The event calendar (holidays, campaigns) in the Streamlit app, with a stand-in for the TimesFM model."""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

pytest.importorskip("streamlit")
import streamlit as st
from streamlit.testing.v1 import AppTest

import callcenter_lab
import callcenter_lab.model as model_module

ROOT = Path(__file__).resolve().parent.parent
APP = str(Path(callcenter_lab.__file__).with_name("app.py"))
CALLS: list[dict] = []  # what the stand-in model received, in order


class RecordingModel:
    def predict(self, history, horizon, return_quantiles, make_positive, **kwargs):
        CALLS.append({"history": np.asarray(history), "horizon": horizon, **kwargs})
        point = np.resize(history[-48:], horizon).astype(float)
        quantiles = np.stack([point * (0.8 + 0.05 * i) for i in range(9)], axis=1)
        return SimpleNamespace(forecast=point, quantiles=quantiles)


@pytest.fixture
def app(monkeypatch):
    CALLS.clear()
    st.cache_resource.clear()
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr(model_module, "load_forecaster", lambda backend="auto", **kwargs: RecordingModel())
    return AppTest.from_file(APP, default_timeout=120).run()


def load_example_calendar(at):
    at.selectbox(key="events_choice").select("eventos_exemplo.csv")
    at.run()
    assert not at.exception, at.exception


def click(at, label):
    next(b for b in at.button if b.label == label).click()
    at.run()
    assert not at.exception, at.exception


def test_without_a_calendar_there_is_no_event_choice(app):
    assert not [r for r in app.radio if r.label == "Como usar os eventos na previsão"]


def test_example_calendar_is_listed_and_offers_three_modes(app):
    load_example_calendar(app)
    modes = next(r for r in app.radio if r.label == "Como usar os eventos na previsão")
    assert modes.options == ["Ajuste pelo efeito informado", "Covariáveis do modelo", "Não usar os eventos"]
    assert modes.value == "Ajuste pelo efeito informado"  # the default: the one that works


def test_adjust_mode_sends_a_cleaned_history_and_no_covariates(app):
    load_example_calendar(app)
    click(app, "Prever")
    assert not app.error
    assert "past_future_covariates" not in CALLS[-1]
    assert CALLS[-1]["horizon"] == 48


def test_covariates_mode_sends_one_row_per_event_kind_covering_history_and_future(app):
    load_example_calendar(app)
    next(r for r in app.radio if r.label == "Como usar os eventos na previsão").set_value("Covariáveis do modelo")
    app.run()
    click(app, "Prever")
    sent = CALLS[-1]
    covariates = sent["past_future_covariates"]
    assert covariates.shape[1] == len(sent["history"]) + sent["horizon"]
    assert covariates.shape[0] >= 1


def test_not_using_the_events_is_the_plain_forecast(app):
    load_example_calendar(app)
    next(r for r in app.radio if r.label == "Como usar os eventos na previsão").set_value("Não usar os eventos")
    app.run()
    click(app, "Prever")
    assert "past_future_covariates" not in CALLS[-1]


def test_reality_check_compares_no_events_covariates_and_adjustment(app):
    load_example_calendar(app)
    click(app, "Rodar teste de realidade")
    assert not app.error
    assert any(s.value == "Com e sem eventos" for s in app.subheader)
    # three backtests ran with the stand-in: plain, with covariates, with the adjustment
    assert sum("past_future_covariates" in call for call in CALLS) == 1
    assert len(CALLS) == 3


def test_staffing_forecast_uses_the_chosen_event_mode(app):
    load_example_calendar(app)
    next(r for r in app.radio if r.label == "Como usar os eventos na previsão").set_value("Covariáveis do modelo")
    app.run()
    click(app, "Dimensionar")
    assert "past_future_covariates" in CALLS[-1]
    assert app.session_state["staffing"]["range"] is not None
