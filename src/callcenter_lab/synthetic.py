"""Synthetic call-center volumes, for use offline and in tests."""

from __future__ import annotations

import numpy as np
import pandas as pd

# Mon..Sun multipliers: busy Mondays, quiet Fridays and Saturdays, closed on Sundays.
_DAY_FACTOR = np.array([1.25, 1.05, 1.0, 1.0, 0.85, 0.5, 0.0])


def _expected_calls(index: pd.DatetimeIndex) -> np.ndarray:
    """Expected calls per 30-minute interval at each timestamp (the rate behind the Poisson counts)."""
    hour = (index.hour + index.minute / 60).to_numpy()
    weekday = index.day_of_week.to_numpy()
    open_weekday = (weekday < 5) & (hour >= 8) & (hour < 20)
    open_saturday = (weekday == 5) & (hour >= 8) & (hour < 14)
    is_open = open_weekday | open_saturday
    profile = 25 + 70 * np.exp(-((hour - 10.5) ** 2) / 4.5) + 45 * np.exp(-((hour - 15.5) ** 2) / 5.0)
    return profile * _DAY_FACTOR[weekday] * is_open


def _grid(weeks: int, start: str) -> pd.DatetimeIndex:
    # Drop the last (closed) Sunday so the series ends on a Saturday with calls in it.
    return pd.date_range(start, periods=weeks * 7 * 48 - 48, freq="30min")


def make_synthetic_calls(
    weeks: int = 12, start: str = "2024-03-04", seed: int = 42
) -> pd.DataFrame:
    """Calls offered per 30 minutes for a contact center.

    Open Mon-Fri 08:00-20:00 and Sat 08:00-14:00, closed on Sundays (zero calls), with a
    late-morning peak, a smaller mid-afternoon peak and Poisson noise.
    Starts on a Monday and ends on a Saturday night. Columns: ``timestamp`` and ``calls_offered``.
    """
    rng = np.random.default_rng(seed)
    index = _grid(weeks, start)
    return pd.DataFrame({"timestamp": index, "calls_offered": rng.poisson(_expected_calls(index))})


def make_synthetic_events() -> pd.DataFrame:
    """An example event calendar for the default 12 weeks: two holidays and three campaigns.

    ``effect`` is the volume multiplier the generator applies on those days (0.3 = 70% fewer calls).
    """
    rows = [
        ("2024-03-18", "2024-03-20", "campanha", 1.5, "Campanha de cobrança"),
        ("2024-03-29", None, "feriado", 0.3, "Sexta-feira Santa"),
        ("2024-04-22", "2024-04-23", "campanha", 1.5, "Campanha de renegociação"),
        ("2024-05-01", None, "feriado", 0.3, "Dia do Trabalho"),
        ("2024-05-24", "2024-05-25", "campanha", 1.5, "Campanha de fim de mês"),
    ]
    frame = pd.DataFrame(rows, columns=["data", "fim", "tipo", "efeito", "nome"])
    return frame


def make_synthetic_calls_with_events(
    weeks: int = 12, start: str = "2024-03-04", seed: int = 42, events: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Like ``make_synthetic_calls`` but the volume follows the event calendar (see ``make_synthetic_events``)."""
    from .events import parse_events

    calendar = parse_events(make_synthetic_events() if events is None else events)
    rng = np.random.default_rng(seed)
    index = _grid(weeks, start)
    rate = _expected_calls(index)
    days = index.normalize()
    for event in calendar.itertuples():
        multiplier = 1.0 if np.isnan(event.effect) else float(event.effect)
        rate = np.where((days >= event.start) & (days <= event.end), rate * multiplier, rate)
    return pd.DataFrame({"timestamp": index, "calls_offered": rng.poisson(rate)})
