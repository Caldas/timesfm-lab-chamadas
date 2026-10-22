"""Exercise the Streamlit app (staffing tab) with a stand-in for the TimesFM model."""

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
    """Predicts 'the same hours of the last day' with a +-20% band."""

    def predict(self, history, horizon, return_quantiles, make_positive):
        point = np.resize(history[-48:], horizon).astype(float)
        quantiles = np.stack([point * (0.8 + 0.05 * i) for i in range(9)], axis=1)
        return SimpleNamespace(forecast=point, quantiles=quantiles)


@pytest.fixture
def app(monkeypatch):
    st.cache_resource.clear()  # the app caches the model: do not reuse another test's stand-in
    monkeypatch.chdir(ROOT)  # the app looks for ./data
    monkeypatch.setattr(model_module, "load_forecaster", lambda backend="auto", **kwargs: FakeModel())
    return AppTest.from_file(APP, default_timeout=90).run()


def button(at, label):
    return next(b for b in at.button if b.label == label)


def radio(at, label):
    return next(r for r in at.radio if r.label == label)


def metric_labels(at):
    return [m.label for m in at.metric]


def test_app_loads_with_the_staffing_panel_and_tab(app):
    assert not app.exception
    assert [t.label for t in app.tabs][:3] == ["🔮 Previsão", "🧪 Teste de realidade", "👥 Dimensionamento"]
    assert app.number_input(key="cfg_sl_pct").value == 80.0  # example default, editable


def test_size_from_history_without_the_model(app):
    radio(app, "Volume a dimensionar").set_value("Últimos intervalos do histórico")
    app.run()
    button(app, "Dimensionar").click()
    app.run()
    assert not app.exception and not app.error
    plan = app.session_state["staffing"]["plan"]
    assert len(plan) == 48 and plan["agents"].max() > 0
    assert (plan["service_level_pct"] >= 80 - 1e-6).all()
    assert {"Pico de agentes", "Nível de serviço esperado"} <= set(metric_labels(app))


def test_size_from_the_forecast_shows_the_volume_range(app):
    button(app, "Dimensionar").click()
    app.run()
    assert not app.exception and not app.error
    saved = app.session_state["staffing"]
    assert saved["range"] is not None
    assert (saved["range"]["agents_low"] <= saved["range"]["agents_high"]).all()


def test_validate_in_the_simulator(app):
    radio(app, "Volume a dimensionar").set_value("Últimos intervalos do histórico")
    app.run()
    button(app, "Dimensionar").click()
    app.run()
    button(app, "Validar no simulador").click()
    app.run()
    assert not app.exception
    assert "Nível de serviço simulado" in metric_labels(app)
    assert app.session_state["staffing_validation"].n_replications == 10


def test_changing_the_goal_changes_the_result(app):
    radio(app, "Volume a dimensionar").set_value("Últimos intervalos do histórico")
    app.run()
    button(app, "Dimensionar").click()
    app.run()
    base = app.session_state["staffing"]["plan"]["agents"].sum()
    app.number_input(key="cfg_sl_pct").set_value(95.0)
    app.run()
    button(app, "Dimensionar").click()
    app.run()
    assert app.session_state["staffing"]["plan"]["agents"].sum() > base


def test_preset_fills_the_panel(app):
    app.selectbox(key="cfg_preset").select("90-30")
    app.run()
    assert app.number_input(key="cfg_sl_pct").value == 90.0
    assert app.number_input(key="cfg_sl_sec").value == 30.0


def test_invalid_shrinkage_is_reported_and_blocks_sizing(app):
    app.number_input(key="cfg_shr_pauses").set_value(99.0)
    app.number_input(key="cfg_shr_training").set_value(5.0)
    app.run()
    assert any("shrinkage" in e.value.lower() for e in app.error)
    assert any("Corrija a configuração" in i.value for i in app.info)


def test_interval_that_cannot_be_staffed_is_explained(app):
    interval = next(s for s in app.selectbox if s.label == "Intervalo")
    interval.select("Dia")
    app.run()
    assert any("5 a 60 minutos" in w.value for w in app.warning)


def test_forecast_and_reality_check_tabs_still_work(app):
    button(app, "Prever").click()
    app.run()
    assert not app.exception and not app.error
    button(app, "Rodar teste de realidade").click()
    app.run()
    assert not app.exception
    labels = metric_labels(app)
    assert "Erro % ponderado (WAPE)" in labels and "Viés" in labels


def test_default_interval_matches_the_30_minute_sample(app):
    """Regression: adding interval options once moved the default to 15 minutes, doubling the intervals."""
    interval = next(s for s in app.selectbox if s.label == "Intervalo")
    assert interval.value == "30 minutos"
    assert next(m for m in app.metric if m.label == "Intervalos").value == "1344"  # 4 weeks of 30-minute data
    radio(app, "Volume a dimensionar").set_value("Últimos intervalos do histórico")
    app.run()
    button(app, "Dimensionar").click()
    app.run()
    plan = app.session_state["staffing"]["plan"]
    assert (plan.index[1] - plan.index[0]).total_seconds() == 30 * 60
    assert app.session_state["staffing"]["config"].interval_minutes == 30
    assert (plan["calls"] > 0).sum() > 0.2 * len(plan)  # not every other interval empty
