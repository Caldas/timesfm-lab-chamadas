"""Regenerate data/samples/trafego_sintetico.csv."""

from pathlib import Path

from trafego_lab.amostra import make_synthetic_traffic

OUT = Path(__file__).resolve().parent.parent / "data" / "samples" / "trafego_sintetico.csv"

if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    make_synthetic_traffic().to_csv(OUT, index=False)
    print(f"Gerado: {OUT}")
