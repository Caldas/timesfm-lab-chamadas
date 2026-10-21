"""Compatibility helpers for running TimesFM 3.0 on older PyTorch.

Intel Macs are stuck on PyTorch 2.2.x (newer releases ship no macOS x86_64 wheels), but the
TimesFM 3.0 PyTorch code uses ``torch.nn.RMSNorm``, which only exists from PyTorch 2.4.
``ensure_rmsnorm`` adds an equivalent layer when it is missing.
"""

from __future__ import annotations


def make_rmsnorm_class():
    """Build a drop-in replacement for ``torch.nn.RMSNorm`` (same parameters and state dict)."""
    import torch
    from torch import nn

    class RMSNorm(nn.Module):
        def __init__(self, normalized_shape, eps=None, elementwise_affine=True, device=None,
                     dtype=None):
            super().__init__()
            if isinstance(normalized_shape, int):
                normalized_shape = (normalized_shape,)
            self.normalized_shape = tuple(normalized_shape)
            self.eps = eps
            if elementwise_affine:
                self.weight = nn.Parameter(
                    torch.ones(self.normalized_shape, device=device, dtype=dtype)
                )
            else:
                self.register_parameter("weight", None)

        def forward(self, x):
            eps = self.eps if self.eps is not None else torch.finfo(x.dtype).eps
            dims = tuple(range(-len(self.normalized_shape), 0))
            out = x * torch.rsqrt(x.pow(2).mean(dims, keepdim=True) + eps)
            return out if self.weight is None else out * self.weight

    return RMSNorm


def ensure_rmsnorm() -> bool:
    """Patch ``torch.nn.RMSNorm`` if this PyTorch lacks it. Returns True if it patched."""
    from torch import nn

    if hasattr(nn, "RMSNorm"):
        return False
    nn.RMSNorm = make_rmsnorm_class()
    return True
