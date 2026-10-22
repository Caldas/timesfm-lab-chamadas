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
    counts_from_timestamps,
    download_dataset,
    parse_hyndman,
    parse_nyc_hourly,
    parse_technion_month,
)

ROOT = Path(__file__).resolve().parent.parent
HEADER = (
    "vru.line\tcall_id\tcustomer_id\tpriority\ttype\tdate\tvru_entry\tvru_exit\tvru_time\tq_start"
    "\tq_exit\tq_time\toutcome\tser_start\tser_exit\tser_time\tserver\tday.of.week"
)


def technion_text(*times):
    # Like the real files: the header has one name fewer than the rows (they start with a row number)
    rows = [
        f"{i}\tAA0101\t3311{i}\t0\t2\tPS\t990101\t{t}\t{t}\t5\t{t}\t0:00:09\t0\tHANG\t0:00:00\t0:00:00\t0\tNO_SERVER\tfriday"
        for i, t in enumerate(times, start=1)
    ]
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


def test_parse_hyndman_grid_to_regular_5min_series():
    out = parse_hyndman(HYNDMAN_TEXT).set_index("timestamp")["calls_offered"]
    assert out.loc["2003-03-03 07:05"] == 11
    assert out.loc["2003-03-04 07:00"] == 20
    assert out.loc["2003-03-03 08:00"] == 0  # no data between the two days: closed
    assert pd.infer_freq(out.index) == "5min"


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
