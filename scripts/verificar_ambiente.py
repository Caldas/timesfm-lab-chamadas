"""Check that this machine is ready to run the lab (macOS, Ubuntu/Linux and Windows).

Usage:
    python scripts/verificar_ambiente.py                # quick checks, no model download
    python scripts/verificar_ambiente.py --com-modelo   # also loads TimesFM and runs one forecast
"""

from __future__ import annotations

import argparse
import importlib
import os
import platform
import subprocess
import sys
from pathlib import Path

from callcenter_lab.model import choose_backend, choose_device

OK, FAIL = "✅", "❌"
SETUP_HINT = {
    "Darwin": "rode ./scripts/setup_mac.sh de novo",
    "Linux": "rode ./scripts/setup_linux.sh de novo",
    "Windows": r"rode scripts\setup_windows.ps1 de novo",
}.get(platform.system(), "rode o script de instalação do seu sistema de novo")
ROOT = Path(__file__).resolve().parent.parent


def ram_gb() -> float | None:
    """Total RAM in GB, or None if it cannot be read."""
    try:
        system = platform.system()
        if system == "Windows":
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatus()
            status.dwLength = ctypes.sizeof(MemoryStatus)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return status.ullTotalPhys / 1024**3
        if system == "Darwin":
            out = subprocess.run(
                ["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, check=True
            )
            return int(out.stdout.strip()) / 1024**3
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024**3
    except (ValueError, OSError, AttributeError, subprocess.SubprocessError):
        return None


def check_import(name: str, hint: str) -> bool:
    try:
        importlib.import_module(name)
    except Exception as exc:  # noqa: BLE001 - report any import problem
        print(f"{FAIL} {name}: {exc}\n    -> {hint}")
        return False
    print(f"{OK} {name}")
    return True


def check_torch() -> int:
    """PyTorch checks (device, Intel Mac limits). Returns the number of problems found."""
    try:
        import numpy
        import torch
    except ImportError as exc:
        print(f"{FAIL} torch: {exc}\n    -> {SETUP_HINT}")
        return 1

    problems = 0
    device = choose_device("auto")
    if device == "cuda":
        print(f"{OK} torch {torch.__version__} na GPU: {torch.cuda.get_device_name(0)}")
    else:
        print(f"{OK} torch {torch.__version__} na CPU")

    if platform.system() == "Darwin" and platform.machine() == "x86_64":
        if sys.version_info >= (3, 13):
            print(
                f"{FAIL} Mac Intel precisa de Python 3.10 a 3.12 (este é {platform.python_version()})."
                "\n    -> veja docs/06-problemas-comuns.md"
            )
            problems += 1
        if int(numpy.__version__.split(".")[0]) >= 2 and torch.__version__.startswith("2.2"):
            print(
                f"{FAIL} NumPy {numpy.__version__} é incompatível com o PyTorch 2.2."
                "\n    -> rode: pip install 'numpy<2'"
            )
            problems += 1
    if device == "cpu":
        print("ℹ️  Previsão na CPU: funciona, mas é mais lenta. Use históricos e horizontes menores.")
    return problems


def check_windows_path() -> None:
    """Warn about Windows' long-path limit, which can break pip installs in deep folders."""
    if platform.system() == "Windows" and len(str(ROOT)) > 80:
        print(
            f"⚠️  O caminho do projeto é longo ({len(str(ROOT))} caracteres). Se o pip falhar com "
            "'WinError 206', mova o projeto para uma pasta curta (ex.: C:\\timesfm-lab)."
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--com-modelo", action="store_true", help="carrega o modelo e prevê")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # emojis on consoles that default to cp1252

    problems = 0
    print(f"Python {platform.python_version()} em {platform.system()} {platform.machine()}")
    check_windows_path()

    memory = ram_gb()
    if memory is not None:
        print(f"{OK if memory >= 8 else '⚠️ '} Memória: {memory:.0f} GB (recomendado: 8 GB ou mais)")

    for module in ("numpy", "pandas", "streamlit", "plotly", "callcenter_lab"):
        problems += not check_import(module, SETUP_HINT)

    backend = choose_backend("auto")
    print(f"ℹ️  Motor escolhido: {backend}")
    backend_module = "timesfm3.mlx" if backend == "mlx" else "timesfm3"
    problems += not check_import(backend_module, "veja docs/06-problemas-comuns.md")
    if backend == "torch":
        problems += check_torch()

    if args.com_modelo and not problems:
        from callcenter_lab.model import forecast, load_forecaster
        from callcenter_lab.synthetic import make_synthetic_calls

        print("➡️  Carregando o TimesFM 3.0 (a primeira vez baixa os pesos)...")
        model = load_forecaster(backend)
        history = make_synthetic_calls(weeks=3)["calls_offered"].to_numpy()
        result = forecast(model, history, horizon=24)
        print(f"{OK} Previsão de 24 passos gerada. Primeiros valores: {result.point[:3].round(0)}")

    print(f"\n{OK} Tudo certo." if not problems else f"\n{FAIL} {problems} problema(s).")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
