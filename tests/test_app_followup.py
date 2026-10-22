"""The "Acompanhamento do dia" tab of the Streamlit app, with a stand-in for the TimesFM model."""

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


class FakeModel:
    def predict(self, history, horizon, return_quantiles, make_positive, **kwargs):
        point = np.resize(np.asarray(history)[-336:], horizon).astype(float)  # "same hours last week"
        return SimpleNamespace(forecast=point, quantiles=np.stack([point * (0.8 + 0.05 * i) for i in range(9)], axis=1))


@pytest.fixture
def app(monkeypatch):
    st.cache_resource.clear()
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr(model_module, "load_forecaster", lambda backend="auto", **kwargs: FakeModel())
    return AppTest.from_file(APP, default_timeout=120).run()


def click(at, label):
    next(b for b in at.button if b.label == label).click()
    at.run()
    assert not at.exception, at.exception


def test_following_a_past_day_plans_observes_and_reforecasts(app):
    click(app, "Acompanhar o dia")
    assert not app.error
    result = app.session_state["followup"]
    assert result.cutoff.strftime("%H:%M") == "12:00"  # the default: midday
    assert len(result.plan) == 48 and len(result.reforecast) == 24
    assert "plan_wape_remaining" in result.summary and "reforecast_wape_remaining" in result.summary
    labels = [m.label for m in app.metric]
    assert {"Desvio acumulado", "Total planejado no dia", "Projeção do dia"} <= set(labels)


def test_cutoff_at_the_end_of_the_day_has_no_projection(app):
    slider = next(s for s in app.select_slider if s.label.startswith("Já temos os dados"))
    slider.set_value(48)  # all 48 intervals known: the end of the day
    app.run()
    click(app, "Acompanhar o dia")
    result = app.session_state["followup"]
    assert result.reforecast is None
    assert "Projeção do dia" not in [m.label for m in app.metric]


def test_cutoff_before_any_observation_is_explained(app):
    slider = next(s for s in app.select_slider if s.label.startswith("Já temos os dados"))
    slider.set_value(1)  # only the first interval (00:00) is known; the sample call center is closed then
    app.run()
    click(app, "Acompanhar o dia")
    assert not app.exception
    assert app.session_state["followup"].summary["intervals_observed"] == 1
