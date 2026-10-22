"""Calendar of events (holidays, campaigns, incidents) used as covariates of the forecast.

The calendar is a CSV with one event per row. Columns (Portuguese or English names both work):

- ``data`` / ``date``: first day of the event (``2024-04-15`` or ``15/04/2024``);
- ``fim`` / ``end``: last day, optional (default: the same day);
- ``tipo`` / ``type``: the kind of event, e.g. ``feriado`` or ``campanha``; each kind becomes one covariate;
- ``efeito`` / ``effect``: optional expected volume multiplier (1.5 = 50% more calls, 0.3 = 70% fewer,
  0 = closed). Empty means "just mark the day";
- ``nome`` / ``name``: optional label.

The forecasting model does not apply the effect by itself: it receives the events as extra input series and
learns from the history how they relate to the volume.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import IO

import numpy as np
import pandas as pd

from .model import ForecastResult, forecast

_ALIASES = {
    "start": ("data", "date", "inicio", "início", "start"),
    "end": ("fim", "end"),
    "kind": ("tipo", "type", "kind"),
    "effect": ("efeito", "effect"),
    "name": ("nome", "name", "descricao", "descrição"),
}
EVENT_COLUMNS = ["start", "end", "kind", "effect", "name"]


def _filled(column: pd.Series) -> pd.Series:
    """True where a cell has something in it (not empty, not NaN)."""
    return column.notna() & (column.astype(str).str.strip() != "")


def _dates(column: pd.Series) -> pd.Series:
    """Parse dates: ISO (2024-03-29) first, then day-first (29/03/2024) for whatever is left."""
    parsed = pd.to_datetime(column, errors="coerce", format="ISO8601")
    rest = parsed.isna() & _filled(column)
    if rest.any():
        parsed[rest] = pd.to_datetime(column[rest], errors="coerce", dayfirst=True)
    return parsed.dt.normalize()


def parse_events(raw: pd.DataFrame) -> pd.DataFrame:
    """Validate a calendar table and return it with the columns ``start, end, kind, effect, name``."""
    lowered = {str(c).strip().lower(): c for c in raw.columns}
    picked = {field: next((lowered[n] for n in names if n in lowered), None) for field, names in _ALIASES.items()}
    if picked["start"] is None or picked["kind"] is None:
        raise ValueError("O calendário precisa das colunas 'data' e 'tipo' (opcionais: 'fim', 'efeito', 'nome').")

    start = _dates(raw[picked["start"]])
    if start.isna().any():
        rows = ", ".join(str(i + 2) for i in raw.index[start.isna()][:5])
        raise ValueError(f"Data inválida no calendário (linha(s) {rows} do arquivo). Use AAAA-MM-DD ou DD/MM/AAAA.")

    end = start
    if picked["end"]:
        parsed_end = _dates(raw[picked["end"]])
        broken = _filled(raw[picked["end"]]) & parsed_end.isna()
        if broken.any():
            raise ValueError(f"Data de fim inválida no calendário (linha {int(raw.index[broken][0]) + 2} do arquivo).")
        end = parsed_end.fillna(start)
    if (end < start).any():
        raise ValueError("Há evento com a data de fim antes da data de início.")

    kind = raw[picked["kind"]].astype(str).str.strip().str.lower()
    if (~_filled(raw[picked["kind"]])).any():
        raise ValueError("Todo evento precisa de um tipo (ex.: feriado, campanha).")

    effect = pd.Series(np.nan, index=raw.index)
    if picked["effect"]:
        effect = pd.to_numeric(raw[picked["effect"]], errors="coerce")
        if (_filled(raw[picked["effect"]]) & effect.isna()).any():
            raise ValueError("O efeito precisa ser um número (ex.: 1.5 ou 0.3) ou ficar em branco.")
        if (effect < 0).any():
            raise ValueError("O efeito não pode ser negativo (0 = central fechada; 1 = volume normal).")

    name = raw[picked["name"]].fillna("").astype(str).str.strip() if picked["name"] else pd.Series("", index=raw.index)
    frame = pd.DataFrame({"start": start, "end": end, "kind": kind, "effect": effect, "name": name})
    return frame.sort_values("start").reset_index(drop=True)


def load_events(source: str | IO) -> pd.DataFrame:
    """Read and validate a calendar CSV (path or open file; ``,`` or ``;`` separated)."""
    return parse_events(pd.read_csv(source, sep=None, engine="python"))


def events_to_covariates(
    events: pd.DataFrame, index: pd.DatetimeIndex, drop_empty: bool = False
) -> tuple[list[str], np.ndarray]:
    """One covariate row per event kind, aligned with ``index``.

    The value on a day covered by an event is ``effect - 1`` (the expected change: +0.5 for 50% more calls,
    -0.7 for 70% fewer) or ``1.0`` if the event has no effect; it is 0 on days without events of that kind.
    With ``drop_empty`` the kinds with no event inside ``index`` are left out (they would be constant rows).
    Returns the kinds and a float32 matrix of shape ``(kinds, len(index))``.
    """
    kinds = sorted(events["kind"].unique())
    days = index.normalize()
    matrix = np.zeros((len(kinds), len(index)), dtype=np.float32)
    for row, kind in enumerate(kinds):
        for event in events[events["kind"] == kind].itertuples():
            value = 1.0 if math.isnan(event.effect) else float(event.effect) - 1.0
            covered = (days >= event.start) & (days <= event.end)
            # overlapping events of one kind: the strongest wins
            matrix[row, covered] = np.where(
                np.abs(value) > np.abs(matrix[row, covered]), value, matrix[row, covered]
            )
    if drop_empty:
        keep = matrix.any(axis=1)
        kinds, matrix = [k for k, flag in zip(kinds, keep) if flag], matrix[keep]
    return kinds, matrix


def events_in_range(events: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """The events that touch ``[start, end]`` (dates)."""
    return events[(events["end"] >= start.normalize()) & (events["start"] <= end.normalize())]


# --- Adjusting by the declared effect (not learned by the model) ----------------------------------
def event_multipliers(events: pd.DataFrame, index: pd.DatetimeIndex) -> np.ndarray:
    """Volume multiplier for each timestamp from the events that declare an ``effect`` greater than zero.

    1.0 on days without such events; overlapping events multiply. Events with no effect, or with effect 0
    (closed), are ignored here.
    """
    days = index.normalize()
    multiplier = np.ones(len(index))
    for event in events.itertuples():
        if math.isnan(event.effect) or event.effect <= 0:
            continue
        multiplier = np.where((days >= event.start) & (days <= event.end), multiplier * float(event.effect), multiplier)
    return multiplier


def with_event_adjustment(
    predictor: Callable[[np.ndarray, int], ForecastResult], multipliers: np.ndarray
) -> Callable[[np.ndarray, int], ForecastResult]:
    """Wrap a ``(history, horizon) -> ForecastResult`` predictor so that it forecasts the *normal* volume and
    then re-applies the declared effects.

    The history is divided by the multiplier of each past day (so earlier campaigns and holidays do not look like
    normal days to the model) and the forecast is multiplied by the multiplier of each future day. ``multipliers``
    must cover the history and the forecast (one value per interval, in order).
    """
    multipliers = np.asarray(multipliers, dtype=float)

    def adjusted(history: np.ndarray, horizon: int) -> ForecastResult:
        n = len(history)
        if len(multipliers) < n + horizon:
            raise ValueError("Os multiplicadores precisam cobrir o histórico e o futuro.")
        base = predictor(np.asarray(history, dtype=float) / multipliers[:n], horizon)
        future = multipliers[n:n + horizon]
        return ForecastResult(point=base.point * future, quantiles=base.quantiles * future[:, None])

    return adjusted


EVENT_MODES = ("adjust", "covariates", "none")


def forecast_with_events(
    forecaster, history: pd.Series, horizon: int, freq: str, events: pd.DataFrame | None, mode: str = "adjust"
) -> ForecastResult:
    """Forecast the next ``horizon`` intervals of ``history`` using the event calendar.

    ``mode``: ``"adjust"`` (forecast the normal volume and re-apply the declared effects), ``"covariates"``
    (give the events to the model as extra input) or ``"none"``.
    """
    if mode not in EVENT_MODES:
        raise ValueError(f"mode deve ser um destes: {EVENT_MODES}.")
    if events is None or mode == "none":
        return forecast(forecaster, history.to_numpy(), horizon)
    future = pd.date_range(history.index[-1], periods=horizon + 1, freq=freq)[1:]
    full_index = history.index.append(future)
    if mode == "covariates":
        kinds, matrix = events_to_covariates(events, full_index, drop_empty=True)
        return forecast(forecaster, history.to_numpy(), horizon, covariates=matrix if kinds else None)
    predictor = with_event_adjustment(lambda h, n: forecast(forecaster, h, n), event_multipliers(events, full_index))
    return predictor(history.to_numpy(), horizon)
