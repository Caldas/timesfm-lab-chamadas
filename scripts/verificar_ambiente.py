"""Check that this machine is ready to run the lab.

Usage:
    python scripts/verificar_ambiente.py                # quick checks, no model download
    python scripts/verificar_ambiente.py --com-modelo   # also loads TimesFM and runs one forecast
"""

from __future__ import annotations

import argparse
import importlib
import os
import platform
import sys

from trafego_lab.modelo import choose_backend

OK, FAIL = "✅", "❌"


def ram_gb() -> float | None:
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024**3
    except (ValueError, OSError, AttributeError):
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
    """PyTorch checks, mainly for Intel Macs. Returns the number of problems found."""
    try:
        import numpy
        import torch
    except ImportError as exc:
        print(f"{FAIL} torch: {exc}\n    -> rode ./scripts/setup_mac.sh de novo")
        return 1

    problems = 0
    print(f"{OK} torch {torch.__version__} (CPU)")
    if platform.system() == "Darwin" and platform.machine() == "x86_64":
        if sys.version_info >= (3, 13):
            print(f"{FAIL} Mac Intel precisa de Python 3.10 a 3.12 (este é {platform.python_version()})."
                  "\n    -> veja docs/06-problemas-comuns.md")
            problems += 1
        if int(numpy.__version__.split(".")[0]) >= 2 and torch.__version__.startswith("2.2"):
            print(f"{FAIL} NumPy {numpy.__version__} é incompatível com o PyTorch 2.2."
                  "\n    -> rode: pip install 'numpy<2'")
            problems += 1
        print("ℹ️  Mac Intel: a previsão roda na CPU e é mais lenta. Use históricos e horizontes menores.")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--com-modelo", action="store_true", help="carrega o modelo e prevê")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # emojis on consoles that default to cp1252

    problems = 0
    print(f"Python {platform.python_version()} em {platform.system()} {platform.machine()}")

    memory = ram_gb()
    if memory is not None:
        print(f"{OK if memory >= 8 else FAIL} Memória: {memory:.0f} GB (recomendado: 8 GB ou mais)")

    for module in ("numpy", "pandas", "streamlit", "plotly", "trafego_lab"):
        problems += not check_import(module, "rode ./scripts/setup_mac.sh de novo")

    backend = choose_backend("auto")
    print(f"ℹ️  Motor escolhido: {backend}")
    backend_module = "timesfm3.mlx" if backend == "mlx" else "timesfm3"
    problems += not check_import(backend_module, "veja docs/06-problemas-comuns.md")
    if backend == "torch":
        problems += check_torch()

    if args.com_modelo and not problems:
        from trafego_lab.amostra import make_synthetic_traffic
        from trafego_lab.modelo import forecast, load_forecaster

        print("➡️  Carregando o TimesFM 3.0 (a primeira vez baixa os pesos)...")
        model = load_forecaster(backend)
        history = make_synthetic_traffic(weeks=2)["vehicle_count"].to_numpy()
        result = forecast(model, history, horizon=24)
        print(f"{OK} Previsão de 24 passos gerada. Primeiros valores: {result.point[:3].round(0)}")

    print(f"\n{OK} Tudo certo." if not problems else f"\n{FAIL} {problems} problema(s).")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
