"""Download the public call-center datasets into data/raw/<dataset>/.

Usage:
    python scripts/baixar_datasets.py                        # all datasets
    python scripts/baixar_datasets.py technion-bank nyc-311  # only the ones you choose
    python scripts/baixar_datasets.py --lista                # list datasets, sources and licenses
    python scripts/baixar_datasets.py nyc-311 --nyc-ano-inicio 2018 --nyc-ano-fim 2019
    python scripts/baixar_datasets.py --forcar               # download again, ignoring the cache
    python scripts/baixar_datasets.py --kaggle dono/dataset  # any Kaggle dataset (needs a token)

Each dataset becomes data/raw/<id>/<id>.csv (columns: timestamp, calls_offered) plus a SOURCE.md with
the attribution. See data/README.md for the sources and licenses.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from callcenter_lab.datasets import DOWNLOADABLE, REGISTRY, download_dataset

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "data" / "raw"


def print_catalog() -> None:
    for dataset in REGISTRY.values():
        status = "baixável" if dataset.downloadable else "já incluído no repositório"
        print(f"{dataset.id}  [{status}]")
        print(f"    {dataset.title}")
        print(f"    {dataset.summary}")
        print(f"    granularidade: {dataset.granularity} | período: {dataset.period}")
        print(f"    fonte: {dataset.source_url}")
        print(f"    licença/condições: {dataset.license}")
        print()


def find_kaggle() -> str | None:
    """The kaggle executable next to this Python (the venv's), else whatever is on PATH."""
    bin_dir = Path(sys.executable).parent
    for name in ("kaggle", "kaggle.exe"):
        candidate = bin_dir / name
        if candidate.exists():
            return str(candidate)
    return shutil.which("kaggle")


def download_kaggle(slug: str, out_root: Path) -> int:
    if "/" not in slug:
        print(f"❌ '{slug}' não é um slug 'dono/dataset'.")
        return 1
    kaggle = find_kaggle()
    if kaggle is None:
        print("❌ Comando 'kaggle' não encontrado. Rode 'pip install kaggle' no ambiente do projeto.")
        return 1
    dest = out_root / slug.split("/")[1]
    dest.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [kaggle, "datasets", "download", "-d", slug, "-p", str(dest), "--unzip"], check=False
    )
    if result.returncode != 0:
        print("❌ Falha no download. Confira seu token do Kaggle e se aceitou os termos do dataset.")
        return 1
    print(f"✅ Baixado em {dest}. Confira a licença na página do dataset antes de reutilizar.")
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "datasets",
        nargs="*",
        metavar="dataset",
        help=f"quais baixar (sem argumentos: todos). Opções: {', '.join(DOWNLOADABLE)}",
    )
    parser.add_argument("--lista", action="store_true", help="mostra os datasets, fontes e licenças")
    parser.add_argument("--forcar", action="store_true", help="baixa de novo, ignorando o cache")
    parser.add_argument("--saida", type=Path, default=DEFAULT_OUT, help="pasta de destino")
    parser.add_argument("--nyc-ano-inicio", type=int, default=2016)
    parser.add_argument("--nyc-ano-fim", type=int, default=2019)
    parser.add_argument("--kaggle", metavar="DONO/DATASET", help="baixa um dataset do Kaggle")
    args = parser.parse_args()

    if args.lista:
        print_catalog()
        return 0
    if args.kaggle:
        return download_kaggle(args.kaggle, args.saida)

    unknown = [name for name in args.datasets if name not in DOWNLOADABLE]
    if unknown:
        print(f"❌ Dataset desconhecido: {', '.join(unknown)}")
        print(f"   Opções: {', '.join(DOWNLOADABLE)} (veja: python scripts/baixar_datasets.py --lista)")
        return 2
    if args.nyc_ano_fim < args.nyc_ano_inicio:
        print("❌ --nyc-ano-fim não pode ser menor que --nyc-ano-inicio.")
        return 2

    chosen = args.datasets or DOWNLOADABLE
    failures = []
    for name in chosen:
        try:
            download_dataset(
                name,
                args.saida,
                force=args.forcar,
                nyc_years=(args.nyc_ano_inicio, args.nyc_ano_fim),
            )
        except Exception as exc:  # noqa: BLE001 - keep going with the other datasets
            print(f"❌ {name}: {exc}")
            failures.append(name)

    print()
    if failures:
        print(f"❌ Falharam: {', '.join(failures)}. Veja docs/06-problemas-comuns.md")
        return 1
    print(f"✅ Pronto: {', '.join(chosen)}. Abra a interface e escolha o arquivo na barra lateral.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
