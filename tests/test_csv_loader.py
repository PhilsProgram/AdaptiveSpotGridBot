
import csv
from pathlib import Path
import pytest
from src.market_data.csv_loader import load_candles


def write_csv(path, rows, fieldnames=None):
    if fieldnames is None:
        fieldnames = [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)



def valid_rows():
    return [
        {
            "timestamp": "2026-01-01T00:00:00Z",
            "open": "100",
            "high": "105",
            "low": "98",
            "close": "103",
            "volume": "12.5",
        },
        {
            "timestamp": "2026-01-01T01:00:00Z",
            "open": "103",
            "high": "108",
            "low": "101",
            "close": "106",
            "volume": "15.2",
        },
    ]


def test_loads_valid_candles(tmp_path):
    csv_path = tmp_path / "candles.csv"
    write_csv(csv_path, valid_rows())

    candles = load_candles(csv_path)

    assert len(candles) == 2
    assert candles[0]["open"] == 100
    assert candles[0]["high"] == 105
    assert candles[0]["close"] == 103
    assert candles[0]["volume"] == 12.5
    assert candles[0]["timestamp"].isoformat() == "2026-01-01T00:00:00+00:00"


def test_rejects_missing_columns(tmp_path):
    csv_path = tmp_path / "candles.csv"
    write_csv(
        csv_path,
        valid_rows(),
        fieldnames=["timestamp", "open", "high", "low", "close"],
    )

    with pytest.raises(ValueError, match="missing required columns"):
        load_candles(csv_path)


def test_rejects_invalid_price(tmp_path):
    rows = valid_rows()
    rows[0]["close"] = "-5"

    csv_path = tmp_path / "candles.csv"
    write_csv(csv_path, rows)

    with pytest.raises(ValueError, match="Prices must be positive"):
        load_candles(csv_path)


def test_rejects_impossible_candle_range(tmp_path):
    rows = valid_rows()
    rows[0]["high"] = "99"

    csv_path = tmp_path / "candles.csv"
    write_csv(csv_path, rows)

    with pytest.raises(ValueError, match="High is inconsistent"):
        load_candles(csv_path)


def test_rejects_duplicate_timestamps(tmp_path):
    rows = valid_rows()
    rows[1]["timestamp"] = rows[0]["timestamp"]

    csv_path = tmp_path / "candles.csv"
    write_csv(csv_path, rows)

    with pytest.raises(ValueError, match="strictly increasing"):
        load_candles(csv_path)


def test_rejects_negative_volume(tmp_path):
    rows = valid_rows()
    rows[0]["volume"] = "-1"

    csv_path = tmp_path / "candles.csv"
    write_csv(csv_path, rows)

    with pytest.raises(ValueError, match="Volume cannot be negative"):
        load_candles(csv_path)


def test_rejects_timezone_missing_from_timestamp(tmp_path):
    rows = valid_rows()
    rows[0]["timestamp"] = "2026-01-01T00:00:00"

    csv_path = tmp_path / "candles.csv"
    write_csv(csv_path, rows)

    with pytest.raises(ValueError, match="timestamp must include a timezone"):
        load_candles(csv_path)



def test_loads_project_sample_csv():
    project_root = Path(__file__).resolve().parent.parent
    csv_path = project_root / "data" / "sample_candles.csv"

    candles = load_candles(csv_path)

    assert len(candles) == 5
    assert candles[0]["timestamp"].isoformat() == (
        "2026-01-01T00:00:00+00:00"
    )
