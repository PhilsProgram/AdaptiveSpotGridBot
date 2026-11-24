
from datetime import datetime, timedelta, timezone

from src.backtesting.grid_behavior import run_grid_behavior_simulation


def create_test_candles(count: int) -> list[dict]:
    """Create predictable hourly candles for testing."""

    candles = []
    start_time = datetime(2026, 1, 1, tzinfo=timezone.utc)

    for i in range(count):
        close = 100 + (i * 10)

        candles.append({
            "timestamp": start_time + timedelta(hours=i),
            "open": close - 5,
            "high": close + 10,
            "low": close - 10,
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

def test_simulation_records_active_grids_correctly():
    candles = create_test_candles(10)
    config = create_test_config()

    results = run_grid_behavior_simulation(candles, config)

    active_results = [
        result for result in results
        if result["status"] == "active"
    ]

    assert len(active_results) > 0

    for result in active_results:
        assert result["lower_bound"] < result["upper_bound"]
        assert len(result["levels"]) == 11
        assert result["grid_width"] > 0
        assert result["atr"] > 0
        assert result["percentage_spacing"] > 0
        
def test_simulation_does_not_use_future_candles():
    candles = create_test_candles(10)
    config = create_test_config()

    results = run_grid_behavior_simulation(candles, config)

    first_result = results[0]

    expected_candle = candles[4]

    assert first_result["timestamp"] == expected_candle["timestamp"]
    assert first_result["market_price"] == expected_candle["close"]
    
def test_simulation_records_rejected_grids():
    candles = create_test_candles(10)
    config = create_test_config()

    # First candle creates a wide lookback range.
    for i, candle in enumerate(candles):
        if i == 0:
            candle["high"] = 200
            candle["low"] = 100
            candle["open"] = 150
            candle["close"] = 150
        else:
            candle["high"] = 151
            candle["low"] = 149
            candle["open"] = 150
            candle["close"] = 150

    config["maximum_range_atr"] = 7.0

    results = run_grid_behavior_simulation(candles, config)

    rejected_results = [
        result for result in results
        if result["status"] == "rejected"
    ]

    assert len(rejected_results) > 0

    for result in rejected_results:
        assert result["reason"]
        assert result["levels"] == []
        
def test_simulation_continues_after_grid_rejection():
    candles = create_test_candles(10)
    config = create_test_config()

    for i, candle in enumerate(candles):
        if i == 0:
            candle["high"] = 200
            candle["low"] = 100
            candle["open"] = 150
            candle["close"] = 150
        else:
            candle["high"] = 151
            candle["low"] = 149
            candle["open"] = 150
            candle["close"] = 150

    config["maximum_range_atr"] = 7.0

    results = run_grid_behavior_simulation(candles, config)

    statuses = [result["status"] for result in results]

    assert "rejected" in statuses
    assert "active" in statuses

    first_rejection = statuses.index("rejected")

    assert "active" in statuses[first_rejection + 1:]