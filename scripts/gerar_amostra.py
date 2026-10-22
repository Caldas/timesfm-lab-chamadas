"""Regenerate data/samples/chamadas_sinteticas.csv."""

from pathlib import Path

from callcenter_lab.synthetic import make_synthetic_calls

OUT = Path(__file__).resolve().parent.parent / "data" / "samples" / "chamadas_sinteticas.csv"

if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    make_synthetic_calls().to_csv(OUT, index=False)
    print(f"Gerado: {OUT}")
