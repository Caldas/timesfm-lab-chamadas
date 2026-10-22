"""Open the web interface: ``python -m callcenter_lab``.

Run it from the project folder (the one that has ``data/``), or pass ``--data-dir``. Any other
options are handed to Streamlit, e.g. ``--server.port 8502``.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m callcenter_lab",
        description="Abre a interface do TimesFM Lab no navegador.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="pasta com samples/ e raw/ (padrão: ./data)",
    )
    args, streamlit_args = parser.parse_known_args(argv)
    os.environ["CALLCENTER_LAB_DATA"] = str((args.data_dir or Path.cwd() / "data").resolve())

    try:
        from streamlit.web import cli as streamlit_cli
    except ImportError:
        print("Streamlit não está instalado. Rode o script de instalação (veja docs/01-instalar.md).")
        return 1

    sys.argv = ["streamlit", "run", str(Path(__file__).with_name("app.py")), *streamlit_args]
    streamlit_cli.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
