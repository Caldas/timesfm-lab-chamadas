import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from callcenter_lab import datasets
from callcenter_lab.datasets import (
    DOWNLOADABLE,
    REGISTRY,
    aggregate_service_data,
    counts_from_timestamps,
    download_dataset,
    parse_hyndman,
    parse_nyc_hourly,
    parse_technion_calls,
    parse_technion_month,
)

ROOT = Path(__file__).resolve().parent.parent
HEADER = (
    "vru.line\tcall_id\tcustomer_id\tpriority\ttype\tdate\tvru_entry\tvru_exit\tvru_time\tq_start"
    "\tq_exit\tq_time\toutcome\tser_start\tser_exit\tser_time\tserver\tday.of.week"
)


def technion_text(*calls):
    """Rows like the real files. Each call is a time string (answered at once, 60 s with the agent) or a
    tuple (time, outcome, queue_seconds, service_seconds). The header has one name fewer than the rows
    (they start with a row number), as in the real files."""
    rows = []
    for i, call in enumerate(calls, start=1):
        t, outcome, q_time, ser_time = (call, "AGENT", 0, 60) if isinstance(call, str) else call
        rows.append(
            f"{i}\tAA0101\t3311{i}\t0\t2\tPS\t990101\t{t}\t{t}\t5\t{t}\t0:00:09\t{q_time}\t{outcome}"
            f"\t0:00:00\t0:00:00\t{ser_time}\tNO_SERVER\tfriday"
        )
    return "\n".join([HEADER, *rows]) + "\n"


HYNDMAN_TEXT = "\t3/3/2003\t04/03/2003\n7:00\t10\t20\n7:05\t11\t21\n"
NYC_ROWS = [
    {"day": "2019-01-01T00:00:00.000", "hour": "0", "calls": "182"},
    {"day": "2019-01-01T00:00:00.000", "hour": "2", "calls": "151"},
]


def test_registry_is_complete():
    for dataset in REGISTRY.values():
        assert dataset.source_url.startswith("http")
        assert dataset.license and dataset.attribution and dataset.granularity and dataset.period
    assert set(DOWNLOADABLE) == {"technion-bank", "hyndman-bank", "nyc-311"}


def test_every_dataset_is_documented_in_data_readme():
    readme = (ROOT / "data" / "README.md").read_text(encoding="utf-8")
    for dataset in REGISTRY.values():
        assert f"`{dataset.id}`" in readme, dataset.id
        assert dataset.source_url in readme, dataset.id


def test_counts_from_timestamps_fills_empty_intervals_with_zero():
    stamps = pd.to_datetime(["2024-01-01 00:05", "2024-01-01 00:10", "2024-01-01 01:10"])
    out = counts_from_timestamps(stamps, "30min")
    assert list(out["calls_offered"]) == [2, 0, 1]


def test_parse_technion_month():
    stamps = parse_technion_month(technion_text("0:00:31", "0:10:00", "0:40:00"))
    assert list(stamps) == list(pd.to_datetime(["1999-01-01 00:00:31", "1999-01-01 00:10:00",
                                                "1999-01-01 00:40:00"]))
    assert list(counts_from_timestamps(stamps)["calls_offered"]) == [2, 1]


def test_parse_technion_calls_reads_outcome_wait_and_handling_time():
    text = technion_text(("0:00:31", "AGENT", 12, 200), ("0:10:00", "HANG", 45, 0), ("0:40:00", "PHANTOM", 3, 0))
    calls = parse_technion_calls(text)
    assert list(calls["outcome"]) == ["AGENT", "HANG", "PHANTOM"]
    assert list(calls["wait_seconds"]) == [12, 45, 3]
    assert list(calls["handle_seconds"]) == [200, 0, 0]


def test_aggregate_service_data_per_interval():
    text = technion_text(
        ("0:00:31", "AGENT", 10, 200),   # answered within 20 s
        ("0:10:00", "AGENT", 30, 100),   # answered, but after 20 s
        ("0:20:00", "HANG", 50, 0),      # hung up
        ("0:40:00", "PHANTOM", 3, 0),    # other
    )
    out = aggregate_service_data(parse_technion_calls(text), "30min", threshold_seconds=20)
    first, second = out.iloc[0], out.iloc[1]
    assert (first["calls_offered"], first["calls_answered"], first["calls_abandoned"], first["calls_other"]) == (3, 2, 1, 0)
    assert first["aht_seconds"] == 150.0  # mean of 200 and 100
    assert first["avg_wait_seconds"] == 20.0  # mean of 10 and 30, answered calls only
    assert first["service_level_pct"] == pytest.approx(100 / 3, abs=0.1)  # 1 of 3 offered answered in 20 s
    assert (second["calls_offered"], second["calls_other"]) == (1, 1)
    assert pd.isna(second["aht_seconds"]) and second["service_level_pct"] == 0.0


def test_aggregate_service_data_fills_empty_intervals_with_zero_counts():
    text = technion_text(("0:05:00", "AGENT", 0, 60), ("2:05:00", "AGENT", 0, 60))
    out = aggregate_service_data(parse_technion_calls(text), "30min")
    assert len(out) == 5 and list(out["calls_offered"]) == [1, 0, 0, 0, 1]
    assert pd.isna(out["service_level_pct"].iloc[1])  # nothing offered: undefined, not zero


def test_parse_hyndman_grid_to_regular_5min_series():
    out = parse_hyndman(HYNDMAN_TEXT).set_index("timestamp")["calls_offered"]
    assert out.loc["2003-03-03 07:05"] == 11
    assert out.loc["2003-03-04 07:00"] == 20
    assert out.loc["2003-03-03 08:00"] == 0  # no data between the two days: closed
    assert (out.index[1] - out.index[0]) == pd.Timedelta(minutes=5)


def test_parse_nyc_hourly_fills_missing_hours():
    out = parse_nyc_hourly(NYC_ROWS)
    assert list(out["calls_offered"]) == [182, 0, 151]


def test_download_hyndman_with_fake_fetch_and_cache(tmp_path):
    calls = []

    def fake(url):
        calls.append(url)
        return HYNDMAN_TEXT.encode()

    messages = []
    csv_path = download_dataset("hyndman-bank", tmp_path, fetch=fake, log=messages.append)
    assert csv_path.exists()
    assert (csv_path.parent / "SOURCE.md").read_text(encoding="utf-8").startswith("# Banco norte-americano")
    assert pd.read_csv(csv_path).columns.tolist() == ["timestamp", "calls_offered"]

    download_dataset("hyndman-bank", tmp_path, fetch=fake, log=messages.append)  # second run
    assert len(calls) == 1
    assert any("REUSO" in m for m in messages)


def test_download_technion_with_fake_fetch(tmp_path):
    def fake(url):
        month = url.rsplit("/", 1)[1].split(".")[0]
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(f"{month}.txt", technion_text("0:00:31", "0:40:00"))
        return buffer.getvalue()

    csv_path = download_dataset("technion-bank", tmp_path, fetch=fake, log=lambda m: None)
    df = pd.read_csv(csv_path)
    assert df["calls_offered"].sum() == 2 * 12  # the same two calls in each of the 12 files
    assert {"calls_answered", "calls_abandoned", "aht_seconds", "avg_wait_seconds", "service_level_pct"} <= set(df.columns)
    assert df["calls_answered"].sum() == 2 * 12


def test_download_nyc_with_fake_fetch(tmp_path):
    csv_path = download_dataset(
        "nyc-311", tmp_path, fetch=lambda url: json.dumps(NYC_ROWS).encode(),
        nyc_years=(2019, 2019), log=lambda m: None,
    )
    assert pd.read_csv(csv_path)["calls_offered"].tolist() == [182, 0, 151]


def test_download_rejects_unknown_and_synthetic(tmp_path):
    with pytest.raises(KeyError):
        download_dataset("nope", tmp_path)
    with pytest.raises(KeyError):
        download_dataset("synthetic", tmp_path)


def test_script_lists_and_validates_arguments():
    script = str(ROOT / "scripts" / "baixar_datasets.py")
    listing = subprocess.run([sys.executable, script, "--lista"], capture_output=True, text=True,
                             encoding="utf-8", check=False)
    assert listing.returncode == 0
    for dataset_id in REGISTRY:
        assert dataset_id in listing.stdout
    bad = subprocess.run([sys.executable, script, "nao-existe"], capture_output=True, text=True,
                         encoding="utf-8", check=False)
    assert bad.returncode == 2


def test_module_exposes_http_get():
    assert callable(datasets.http_get)
