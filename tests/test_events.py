import io
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from callcenter_lab.events import (
    event_multipliers,
    events_in_range,
    events_to_covariates,
    forecast_with_events,
    load_events,
    parse_events,
    with_event_adjustment,
)
from callcenter_lab.model import forecast
from callcenter_lab.synthetic import (
    make_synthetic_calls,
    make_synthetic_calls_with_events,
    make_synthetic_events,
)

CSV = """data,fim,tipo,efeito,nome
2024-03-29,,feriado,0.3,Sexta-feira Santa
2024-03-18,2024-03-20,campanha,1.5,Cobrança
2024-05-10,,incidente,,Falha no sistema
"""


def calendar():
    return load_events(io.StringIO(CSV))


def test_parse_events_normalises_and_sorts():
    events = calendar()
    assert list(events.columns) == ["start", "end", "kind", "effect", "name"]
    assert list(events["kind"]) == ["campanha", "feriado", "incidente"]  # sorted by date
    assert events.loc[0, "end"] == pd.Timestamp("2024-03-20")
    assert events.loc[1, "end"] == events.loc[1, "start"]  # no end date: a single day
    assert np.isnan(events.loc[2, "effect"]) and events.loc[1, "effect"] == 0.3


def test_english_headers_dayfirst_dates_and_semicolons():
    text = "date;type;effect\n29/03/2024;Holiday;0.3\n"
    events = load_events(io.StringIO(text))
    assert events.loc[0, "start"] == pd.Timestamp("2024-03-29") and events.loc[0, "kind"] == "holiday"


@pytest.mark.parametrize(
    "text,message",
    [
        ("tipo\nferiado\n", "colunas"),
        ("data,tipo\nontem,feriado\n", "Data inválida"),
        ("data,fim,tipo\n2024-03-20,2024-03-18,campanha\n", "antes"),
        ("data,fim,tipo\n2024-03-20,xx,campanha\n", "fim inválida"),
        ("data,tipo\n2024-03-20,\n", "tipo"),
        ("data,tipo,efeito\n2024-03-20,feriado,muito\n", "número"),
        ("data,tipo,efeito\n2024-03-20,feriado,-1\n", "negativo"),
    ],
)
def test_invalid_calendars_are_explained(text, message):
    with pytest.raises(ValueError, match=message):
        load_events(io.StringIO(text))


def test_covariates_one_row_per_kind_with_effect_minus_one():
    index = pd.date_range("2024-03-17", periods=7 * 48, freq="30min")  # Sunday 17th .. Saturday 23rd
    kinds, matrix = events_to_covariates(calendar(), index)
    assert kinds == ["campanha", "feriado", "incidente"]
    assert matrix.shape == (3, len(index)) and matrix.dtype == np.float32
    days = index.normalize()
    campaign = matrix[0]
    assert set(campaign[(days >= "2024-03-18") & (days <= "2024-03-20")]) == {0.5}  # 1.5x -> +0.5
    assert set(campaign[(days < "2024-03-18") | (days > "2024-03-20")]) == {0.0}
    assert not matrix[1].any()  # the holiday is outside this window


def test_covariate_value_is_one_when_there_is_no_effect_and_negative_for_a_drop():
    index = pd.date_range("2024-03-29", periods=48, freq="30min")
    _, holiday = events_to_covariates(calendar(), index)
    assert np.allclose(holiday[1], -0.7)  # 0.3x -> -0.7
    index = pd.date_range("2024-05-10", periods=48, freq="30min")
    kinds, incident = events_to_covariates(calendar(), index)
    assert set(incident[kinds.index("incidente")]) == {1.0}  # marked only


def test_overlapping_events_of_one_kind_keep_the_strongest():
    events = parse_events(pd.DataFrame({
        "data": ["2024-03-18", "2024-03-19"], "fim": ["2024-03-20", "2024-03-19"],
        "tipo": ["campanha", "campanha"], "efeito": [1.2, 2.0],
    }))
    index = pd.date_range("2024-03-18", periods=3 * 48, freq="30min")
    _, matrix = events_to_covariates(events, index)
    per_day = [matrix[0][i * 48:(i + 1) * 48] for i in range(3)]
    assert np.allclose(per_day[0], 0.2) and np.allclose(per_day[1], 1.0) and np.allclose(per_day[2], 0.2)


def test_events_in_range():
    inside = events_in_range(calendar(), pd.Timestamp("2024-03-19 10:00"), pd.Timestamp("2024-03-30"))
    assert list(inside["kind"]) == ["campanha", "feriado"]
    assert events_in_range(calendar(), pd.Timestamp("2024-06-01"), pd.Timestamp("2024-06-02")).empty


# --- forecast with covariates ---------------------------------------------------------------------


class RecordingModel:
    def __init__(self):
        self.kwargs = None

    def predict(self, history, horizon, return_quantiles, make_positive, **kwargs):
        self.kwargs = kwargs
        point = np.ones(horizon)
        return SimpleNamespace(forecast=point, quantiles=np.stack([point] * 9, axis=1))


def test_forecast_passes_covariates_as_past_future_covariates():
    model = RecordingModel()
    covariates = np.zeros((2, 10 + 4))
    forecast(model, np.arange(10.0), 4, covariates=covariates)
    assert model.kwargs["past_future_covariates"].shape == (2, 14)
    forecast(model, np.arange(10.0), 4)
    assert model.kwargs == {}  # nothing extra without covariates


def test_forecast_rejects_covariates_that_do_not_cover_history_and_future():
    with pytest.raises(ValueError, match="cobrir"):
        forecast(RecordingModel(), np.arange(10.0), 4, covariates=np.zeros((1, 10)))


# --- synthetic data with events ---------------------------------------------------------------------


def test_synthetic_events_follow_the_calendar():
    plain = make_synthetic_calls().set_index("timestamp")["calls_offered"]
    with_events = make_synthetic_calls_with_events().set_index("timestamp")["calls_offered"]
    day = lambda s, d: s.loc[d].sum()
    assert day(with_events, "2024-03-29") < 0.5 * day(plain, "2024-03-29")  # holiday: ~0.3x
    assert day(with_events, "2024-03-19") > 1.3 * day(plain, "2024-03-19")  # campaign: ~1.5x
    assert day(with_events, "2024-03-12") == pytest.approx(day(plain, "2024-03-12"), rel=0.25)  # ordinary day
    assert len(with_events) == len(plain)
    assert parse_events(make_synthetic_events())["kind"].nunique() == 2


# --- adjusting by the declared effect ---------------------------------------------------------------


class MeanModel:
    """Forecasts the mean of the history it receives, and remembers what it was given."""

    def __init__(self):
        self.seen = None
        self.kwargs = None

    def predict(self, history, horizon, return_quantiles, make_positive, **kwargs):
        self.seen, self.kwargs = np.asarray(history), kwargs
        point = np.full(horizon, float(np.mean(history)))
        return SimpleNamespace(forecast=point, quantiles=np.stack([point * (0.8 + 0.05 * i) for i in range(9)], axis=1))


def daily_series():
    """Four days of 2 intervals each: day 2 is a campaign (x2) and day 4 (the future) is a campaign too."""
    index = pd.date_range("2024-03-01", periods=8, freq="12h")
    return pd.Series([10, 10, 20, 20, 10, 10, 10, 10], index=index[:8], dtype=float)


def campaign_calendar():
    return parse_events(pd.DataFrame({"data": ["2024-03-02", "2024-03-04"], "tipo": ["campanha", "campanha"], "efeito": [2.0, 2.0]}))


def test_event_multipliers_ignore_events_without_effect_or_closed_days():
    events = parse_events(pd.DataFrame({
        "data": ["2024-03-01", "2024-03-02", "2024-03-03"], "tipo": ["a", "b", "c"], "efeito": [2.0, None, 0.0]}))
    index = pd.date_range("2024-03-01", periods=3 * 2, freq="12h")
    assert list(event_multipliers(events, index)) == [2.0, 2.0, 1.0, 1.0, 1.0, 1.0]


def test_adjustment_cleans_the_history_and_reapplies_the_effect_in_the_future():
    series = daily_series().iloc[:6]  # 3 days of history (day 2 is a campaign), then 1 future day (the 4th)
    model = MeanModel()
    full_index = series.index.append(pd.date_range(series.index[-1], periods=3, freq="12h")[1:])
    result = with_event_adjustment(lambda h, n: forecast(model, h, n), event_multipliers(campaign_calendar(), full_index))(
        series.to_numpy(), 2)
    assert list(model.seen) == [10, 10, 10, 10, 10, 10]  # the campaign day was brought back to normal
    assert list(result.point) == [20, 20]  # the future campaign day is back at x2
    assert result.quantiles.shape == (2, 9) and np.allclose(result.quantiles[:, 4], 20)


def test_adjustment_needs_multipliers_for_the_whole_window():
    predictor = with_event_adjustment(lambda h, n: None, np.ones(5))
    with pytest.raises(ValueError, match="cobrir"):
        predictor(np.ones(5), 2)


def test_forecast_with_events_modes():
    history = daily_series().iloc[:6]
    plain, cov, adj = MeanModel(), MeanModel(), MeanModel()
    base = forecast_with_events(plain, history, 2, "12h", campaign_calendar(), "none")
    assert plain.kwargs == {} and list(base.point) == [pytest.approx(history.mean())] * 2
    forecast_with_events(cov, history, 2, "12h", campaign_calendar(), "covariates")
    assert cov.kwargs["past_future_covariates"].shape == (1, 8)  # one kind, history 6 + horizon 2
    result = forecast_with_events(adj, history, 2, "12h", campaign_calendar(), "adjust")
    assert adj.kwargs == {} and list(result.point) == [20, 20]
    assert forecast_with_events(MeanModel(), history, 2, "12h", None, "adjust").point.shape == (2,)  # no calendar: plain
    with pytest.raises(ValueError):
        forecast_with_events(MeanModel(), history, 2, "12h", campaign_calendar(), "magia")
