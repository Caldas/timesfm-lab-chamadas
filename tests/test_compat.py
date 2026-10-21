import pytest

torch = pytest.importorskip("torch")

from trafego_lab.compat import ensure_rmsnorm, make_rmsnorm_class


@pytest.mark.skipif(not hasattr(torch.nn, "RMSNorm"), reason="needs native RMSNorm to compare")
def test_fallback_rmsnorm_matches_native():
    x = torch.randn(2, 5, 16)
    native = torch.nn.RMSNorm(16)
    ours = make_rmsnorm_class()(16)
    torch.nn.init.normal_(native.weight)
    ours.load_state_dict(native.state_dict())
    assert torch.allclose(native(x), ours(x), atol=1e-6)


def test_ensure_rmsnorm_is_noop_when_available():
    if hasattr(torch.nn, "RMSNorm"):
        assert ensure_rmsnorm() is False
