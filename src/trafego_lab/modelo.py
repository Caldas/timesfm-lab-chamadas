"""Thin wrapper around TimesFM 3.0 that picks the right backend for this machine."""

from __future__ import annotations

import importlib.util
import platform
import sys
from dataclasses import dataclass

import numpy as np

CHECKPOINT = "google/timesfm-3.0-pytorch"
# The model returns 9 quantiles: 0.1 ... 0.9
QUANTILE_LEVELS = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)


@dataclass(frozen=True)
class ForecastResult:
    """Point forecast (median) and quantiles, one row per future step."""

    point: np.ndarray  # shape (horizon,)
    quantiles: np.ndarray  # shape (horizon, 9)

    @property
    def lower(self) -> np.ndarray:
        """10% quantile."""
        return self.quantiles[:, 0]

    @property
    def upper(self) -> np.ndarray:
        """90% quantile."""
        return self.quantiles[:, -1]


def choose_backend(requested: str = "auto") -> str:
    """Return ``"mlx"`` or ``"torch"``.

    ``auto`` uses MLX on Apple silicon when installed, otherwise PyTorch on CPU.
    """
    if requested in ("mlx", "torch"):
        return requested
    if requested != "auto":
        raise ValueError("backend deve ser 'auto', 'mlx' ou 'torch'.")
    apple_silicon = sys.platform == "darwin" and platform.machine() == "arm64"
    if apple_silicon and importlib.util.find_spec("mlx") is not None:
        return "mlx"
    return "torch"


def load_forecaster(backend: str = "auto", checkpoint: str = CHECKPOINT):
    """Load TimesFM 3.0. The first call downloads the weights."""
    chosen = choose_backend(backend)
    if chosen == "mlx":
        from timesfm3.mlx import TimesFM3Forecaster

        return TimesFM3Forecaster.from_pretrained(checkpoint)

    from .compat import ensure_rmsnorm

    ensure_rmsnorm()  # Intel Macs only get PyTorch 2.2, which has no nn.RMSNorm
    from timesfm3 import TimesFM3Forecaster

    return TimesFM3Forecaster.from_pretrained(checkpoint, device="cpu")


def forecast(forecaster, context, horizon: int) -> ForecastResult:
    """Forecast ``horizon`` steps ahead from a 1-D history."""
    history = np.asarray(context, dtype=np.float32)
    if history.ndim != 1 or history.size < 2:
        raise ValueError("O histórico precisa ser uma série 1D com ao menos 2 pontos.")
    if horizon < 1:
        raise ValueError("horizon deve ser >= 1.")
    out = forecaster.predict(history, horizon=horizon, return_quantiles=True, make_positive=True)
    return ForecastResult(point=np.asarray(out.forecast), quantiles=np.asarray(out.quantiles))
