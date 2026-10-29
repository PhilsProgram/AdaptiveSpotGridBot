
from src.config_loader import load_config
from src.strategy.grid_builder import build_adaptive_grid


def test_configuration_can_build_adaptive_grid():
    config = load_config()

    count = max(
        config["lookback_candles"],
        config["atr_period"],
    ) + 10

    highs = [101.0 + i * 0.1 for i in range(count)]
    lows = [99.0 + i * 0.1 for i in range(count)]
    closes = [100.0 + i * 0.1 for i in range(count)]

    grid = build_adaptive_grid(
        highs=highs,
        lows=lows,
        closes=closes,
        atr_period=config["atr_period"],
        lookback=config["lookback_candles"],
        intervals=config["grid_intervals"],
        boundary_atr_multiplier=config["boundary_atr_multiplier"],
        minimum_range_atr=config["minimum_range_atr"],
        maximum_range_atr=config["maximum_range_atr"],
    )

    assert len(grid["levels"]) == config["grid_intervals"] + 1
    assert grid["lower_bound"] < grid["upper_bound"]
    assert grid["atr"] > 0