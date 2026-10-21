"""Download a Kaggle dataset into data/raw/<name>/.

Usage:
    python scripts/baixar_kaggle.py --lista
    python scripts/baixar_kaggle.py metro-interstate
    python scripts/baixar_kaggle.py dono/nome-do-dataset      # any dataset slug

Needs a Kaggle account and an API token; see docs/03-baixar-dados-kaggle.md.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"

# Short names -> Kaggle slugs. Always check the license on the dataset page.
SUGGESTED = {
    "metro-interstate": "anshtanwar/metro-interstate-traffic-volume",
    "junctions": "fedesoriano/traffic-prediction-dataset",
}


def resolve_slug(name: str) -> str:
    return SUGGESTED.get(name, name)


def download(slug: str) -> Path:
    if "/" not in slug:
        raise SystemExit(f"❌ '{slug}' não é um nome conhecido nem um slug 'dono/dataset'.")
    kaggle = shutil.which("kaggle")
    if kaggle is None:
        raise SystemExit(
            "❌ Comando 'kaggle' não encontrado. Ative o .venv e rode 'pip install kaggle'. "
            "Veja docs/03-baixar-dados-kaggle.md"
        )
    dest = RAW / slug.split("/")[1]
    dest.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [kaggle, "datasets", "download", "-d", slug, "-p", str(dest), "--unzip"], check=False
    )
    if result.returncode != 0:
        raise SystemExit(
            "❌ Falha no download. Confira seu token do Kaggle e se você aceitou os termos "
            "do dataset no site."
        )
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("dataset", nargs="?", help="nome curto ou slug dono/dataset")
    parser.add_argument("--lista", action="store_true", help="mostra os nomes curtos")
    args = parser.parse_args()

    if args.lista or not args.dataset:
        for short, slug in SUGGESTED.items():
            print(f"{short:18} {slug}")
        return 0
    dest = download(resolve_slug(args.dataset))
    print(f"✅ Baixado em {dest}")
    for csv in sorted(dest.rglob("*.csv")):
        print("   ", csv.relative_to(RAW.parent.parent))
    return 0


if __name__ == "__main__":
    sys.exit(main())
