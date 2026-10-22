"""Synthetic call-center volumes, for use offline and in tests."""

from __future__ import annotations

import numpy as np
import pandas as pd

# Mon..Sun multipliers: busy Mondays, quiet Fridays and Saturdays, closed on Sundays.
_DAY_FACTOR = np.array([1.25, 1.05, 1.0, 1.0, 0.85, 0.5, 0.0])


def make_synthetic_calls(
    weeks: int = 12, start: str = "2024-03-04", seed: int = 42
) -> pd.DataFrame:
    """Calls offered per 30 minutes for a contact center.

    Open Mon-Fri 08:00-20:00 and Sat 08:00-14:00, closed on Sundays (zero calls), with a
    late-morning peak, a smaller mid-afternoon peak and Poisson noise.
    Starts on a Monday and ends on a Saturday night. Columns: ``timestamp`` and ``calls_offered``.
    """
    rng = np.random.default_rng(seed)
    # Drop the last (closed) Sunday so the series ends on a Saturday with calls in it.
    index = pd.date_range(start, periods=weeks * 7 * 48 - 48, freq="30min")
    hour = (index.hour + index.minute / 60).to_numpy()
    weekday = index.dayofweek.to_numpy()

    open_weekday = (weekday < 5) & (hour >= 8) & (hour < 20)
    open_saturday = (weekday == 5) & (hour >= 8) & (hour < 14)
    is_open = open_weekday | open_saturday

    profile = 25 + 70 * np.exp(-((hour - 10.5) ** 2) / 4.5) + 45 * np.exp(-((hour - 15.5) ** 2) / 5.0)
    rate = profile * _DAY_FACTOR[weekday] * is_open
    return pd.DataFrame({"timestamp": index, "calls_offered": rng.poisson(rate)})
