import csv
from datetime import datetime, timedelta, timezone

import pytest

from src.market_data.historical_data import prepare_historical_data


def create_test_csv(path, number_of_candles=100):
    """Create a temporary CSV containing hourly BTC candles."""

    start_time = datetime(2026, 1, 1, tzinfo=timezone.utc)

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        writer.writerow([
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ])

        for i in range(number_of_candles):
            timestamp = start_time + timedelta(hours=i)

            writer.writerow([
                timestamp.isoformat(),
                80000,
                80500,
                79500,
                80200,
                10,
            ])


def test_prepares_completed_historical_candles(tmp_path):
    csv_path = tmp_path / "candles.csv"
    create_test_csv(csv_path)

    result = prepare_historical_data(
        str(csv_path),
        minimum_candles=72,
    )

    assert len(result) == 100
    assert result[0]["close"] == 80200


def test_rejects_insufficient_completed_candles(tmp_path):
    csv_path = tmp_path / "candles.csv"
    create_test_csv(csv_path, number_of_candles=50)

    with pytest.raises(ValueError, match="Not enough completed candles"):
        prepare_historical_data(
            str(csv_path),
            minimum_candles=72,
        )


@pytest.mark.parametrize("minimum", [0, -1, 2.5, True])
def test_rejects_invalid_minimum_candles(tmp_path, minimum):
    csv_path = tmp_path / "candles.csv"
    create_test_csv(csv_path)

    with pytest.raises(ValueError, match="minimum_candles"):
        prepare_historical_data(
            str(csv_path),
            minimum_candles=minimum,
        )


def test_rejects_missing_csv_file(tmp_path):
    missing_file = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError):
        prepare_historical_data(str(missing_file))
