"""Forecast error metrics."""

from __future__ import annotations

import numpy as np


def mae(actual, predicted) -> float:
    """Mean absolute error."""
    a, p = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    return float(np.mean(np.abs(a - p)))


def mape(actual, predicted) -> float:
    """Mean absolute percentage error, in percent. Zero actuals are ignored.

    Returns ``nan`` when every actual value is zero.
    """
    a, p = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    mask = a != 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((a[mask] - p[mask]) / a[mask])) * 100)


def coverage(actual, lower, upper) -> float:
    """Share (0-1) of actual values that fall inside ``[lower, upper]``."""
    a = np.asarray(actual, dtype=float)
    lo, hi = np.asarray(lower, dtype=float), np.asarray(upper, dtype=float)
    return float(np.mean((a >= lo) & (a <= hi)))
