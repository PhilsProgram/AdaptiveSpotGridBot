from datetime import datetime, timedelta, timezone

from src.market_data.csv_loader import filter_completed_candles


def test_completed_candles_are_kept():
    now = datetime.now(timezone.utc)

    candles = [
        {"timestamp": now - timedelta(hours=3)},
        {"timestamp": now - timedelta(hours=2)},
    ]

    result = filter_completed_candles(candles)

    assert len(result) == 2


def test_incomplete_candle_is_removed():
    now = datetime.now(timezone.utc)

    candles = [
        {"timestamp": now - timedelta(hours=2)},
        {"timestamp": now - timedelta(minutes=30)},
    ]

    result = filter_completed_candles(candles)

    assert len(result) == 1
    assert result[0]["timestamp"] == candles[0]["timestamp"]


def test_empty_candle_list():
    result = filter_completed_candles([])

    assert result == []
