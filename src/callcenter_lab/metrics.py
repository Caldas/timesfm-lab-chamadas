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


def wape(actual, predicted) -> float:
    """Weighted absolute percentage error, in percent: ``sum|error| / sum(actual)``.

    The usual accuracy measure for call volumes: unlike MAPE it is not distorted by quiet
    intervals (or closed hours with zero calls). Returns ``nan`` when there were no calls.
    """
    a, p = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    total = a.sum()
    if total == 0:
        return float("nan")
    return float(np.abs(a - p).sum() / total * 100)


def bias_pct(actual, predicted) -> float:
    """Total over/under-forecast, in percent: ``(sum(predicted) - sum(actual)) / sum(actual)``.

    Positive means the forecast asked for more calls than arrived (overstaffing risk), negative
    means fewer (understaffing risk). Returns ``nan`` when there were no calls.
    """
    a, p = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    total = a.sum()
    if total == 0:
        return float("nan")
    return float((p.sum() - total) / total * 100)


def coverage(actual, lower, upper) -> float:
    """Share (0-1) of actual values that fall inside ``[lower, upper]``."""
    a = np.asarray(actual, dtype=float)
    lo, hi = np.asarray(lower, dtype=float), np.asarray(upper, dtype=float)
    return float(np.mean((a >= lo) & (a <= hi)))
