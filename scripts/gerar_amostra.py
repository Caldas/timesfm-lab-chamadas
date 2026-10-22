"""Regenerate the sample files in data/samples/: call volumes and the matching service data."""

from pathlib import Path

from callcenter_lab.synthetic import (
    make_synthetic_calls,
    make_synthetic_calls_with_events,
    make_synthetic_events,
)
from callcenter_lab.wfm import StaffingConfig, generate_dataset, synthetic_aht
from callcenter_lab.wfm.workload import SeriesAHT

SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"

if __name__ == "__main__":
    SAMPLES.mkdir(parents=True, exist_ok=True)
    volume = make_synthetic_calls()
    volume.to_csv(SAMPLES / "chamadas_sinteticas.csv", index=False)
    print(f"Gerado: {SAMPLES / 'chamadas_sinteticas.csv'}")

    # Service data: simulate the same days with a staffing plan for the default goal and callers
    # who hang up after ~2 minutes on average.
    calls = volume.set_index("timestamp")["calls_offered"].astype(float)
    config = StaffingConfig(mean_patience_seconds=120)
    aht = SeriesAHT(synthetic_aht(calls.index, config.aht_seconds), config.aht_seconds)
    service = generate_dataset(calls, config, aht=aht, seed=42)
    numeric = {"aht_seconds": 1, "avg_wait_seconds": 1, "service_level_pct": 1, "occupancy_pct": 1}
    service.round(numeric).to_csv(SAMPLES / "chamadas_sinteticas_atendimento.csv", index=False)
    print(f"Gerado: {SAMPLES / 'chamadas_sinteticas_atendimento.csv'}")

    # Calls that follow an event calendar (holidays and campaigns), plus the calendar itself.
    make_synthetic_calls_with_events().to_csv(SAMPLES / "chamadas_sinteticas_eventos.csv", index=False)
    (SAMPLES / "eventos").mkdir(exist_ok=True)
    make_synthetic_events().to_csv(SAMPLES / "eventos" / "eventos_exemplo.csv", index=False)
    print(f"Gerado: {SAMPLES / 'chamadas_sinteticas_eventos.csv'} e {SAMPLES / 'eventos' / 'eventos_exemplo.csv'}")
