
from datetime import datetime, timedelta, timezone

from src.backtesting.grid_behavior import run_grid_behavior_simulation


def create_test_candles(count: int) -> list[dict]:
    """Create predictable hourly candles for testing."""

    candles = []
    start_time = datetime(2026, 1, 1, tzinfo=timezone.utc)

    for i in range(count):
        close = 100 + (i * 0.1)

        candles.append({
            "timestamp": start_time + timedelta(hours=i),
            "open": close - 0.5,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": 10,
        })

    return candles


def create_test_config() -> dict:
    """Return a small, predictable strategy configuration."""

    return {
        "atr_period": 3,
        "lookback_candles": 5,
        "grid_intervals": 10,
        "boundary_atr_multiplier": 0.5,
        "minimum_range_atr": 6.0,
        "maximum_range_atr": 20.0,
    }


def test_simulation_returns_correct_number_of_calculations():
    candles = create_test_candles(10)
    config = create_test_config()

    results = run_grid_behavior_simulation(candles, config)

    assert len(results) == 6
