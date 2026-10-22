import pytest

from callcenter_lab.model import choose_device


def test_choose_device_explicit_values():
    assert choose_device("cpu") == "cpu"
    assert choose_device("cuda") == "cuda"


def test_choose_device_rejects_unknown():
    with pytest.raises(ValueError):
        choose_device("tpu")


def test_choose_device_env_override(monkeypatch):
    monkeypatch.setenv("CALLCENTER_LAB_DEVICE", "cpu")
    assert choose_device("auto") == "cpu"


def test_choose_device_auto_is_cpu_or_cuda(monkeypatch):
    monkeypatch.delenv("CALLCENTER_LAB_DEVICE", raising=False)
    assert choose_device("auto") in ("cpu", "cuda")
