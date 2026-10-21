"""Synthetic hourly traffic counts, for use offline and in tests."""

from __future__ import annotations

import numpy as np
import pandas as pd


def make_synthetic_traffic(
    weeks: int = 8, start: str = "2024-03-04", seed: int = 42
) -> pd.DataFrame:
    """Hourly vehicle counts with morning/evening peaks, quieter weekends and noise.

    Columns: ``timestamp`` and ``vehicle_count``.
    """
    rng = np.random.default_rng(seed)
    index = pd.date_range(start, periods=weeks * 7 * 24, freq="h")
    hour = index.hour.to_numpy()
    weekend = index.dayofweek.to_numpy() >= 5

    morning = np.exp(-((hour - 8) ** 2) / 4.0)
    evening = np.exp(-((hour - 17.5) ** 2) / 5.0)
    midday = 0.35 * np.exp(-((hour - 13) ** 2) / 18.0)
    weekday_profile = 150 + 850 * morning + 950 * evening + 300 * midday
    weekend_profile = 120 + 450 * np.exp(-((hour - 13) ** 2) / 30.0)

    base = np.where(weekend, weekend_profile, weekday_profile)
    counts = base * rng.normal(1.0, 0.07, size=len(index))
    return pd.DataFrame(
        {"timestamp": index, "vehicle_count": np.maximum(counts, 0).round().astype(int)}
    )
