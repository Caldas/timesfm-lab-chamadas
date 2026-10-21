import io

import pandas as pd
import pytest

from trafego_lab.amostra import make_synthetic_traffic
from trafego_lab.dados import detect_columns, load_csv, prepare_series, resample_series


def test_detect_columns_finds_timestamp_and_count():
    df = make_synthetic_traffic(weeks=1)
    assert detect_columns(df) == ("timestamp", "vehicle_count")


def test_detect_columns_ignores_numeric_columns_as_dates():
    df = pd.DataFrame({"id": [1, 2, 3], "when": ["2024-01-01", "2024-01-02", "2024-01-03"],
                       "volume": [10, 20, 30]})
    assert detect_columns(df) == ("when", "volume")


def test_load_csv_guesses_semicolon_separator():
    df = load_csv(io.StringIO("data;veiculos\n2024-01-01 00:00;5\n2024-01-01 01:00;7\n"))
    assert list(df.columns) == ["data", "veiculos"]


def test_prepare_series_sorts_and_averages_duplicates():
    df = pd.DataFrame({"t": ["2024-01-02", "2024-01-01", "2024-01-01"], "v": [3, 1, 3]})
    series = prepare_series(df, "t", "v")
    assert series.index.is_monotonic_increasing
    assert series.loc["2024-01-01"] == 2


def test_prepare_series_rejects_empty():
    df = pd.DataFrame({"t": ["x"], "v": ["y"]})
    with pytest.raises(ValueError):
        prepare_series(df, "t", "v")


def test_resample_sum_and_gap_fill():
    index = pd.to_datetime(["2024-01-01 00:00", "2024-01-01 00:30", "2024-01-01 02:00"])
    series = pd.Series([10.0, 20.0, 40.0], index=index)
    hourly = resample_series(series, "h", how="sum")
    assert list(hourly.index.hour) == [0, 1, 2]
    assert hourly.iloc[0] == 30
    assert hourly.iloc[1] == 35  # interpolated between 30 and 40
