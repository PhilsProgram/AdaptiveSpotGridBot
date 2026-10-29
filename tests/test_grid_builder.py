
import pytest

from src.strategy.grid_builder import build_adaptive_grid


def make_candles(count=80):
    highs = [101.0 + i * 0.1 for i in range(count)]
    lows = [99.0 + i * 0.1 for i in range(count)]
    closes = [100.0 + i * 0.1 for i in range(count)]
    return highs, lows, closes


def test_builds_valid_adaptive_grid():
    highs, lows, closes = make_candles()

    grid = build_adaptive_grid(highs, lows, closes)

    assert grid["atr"] > 0
    assert grid["lower_bound"] > 0
    assert grid["upper_bound"] > grid["lower_bound"]
    assert len(grid["levels"]) == 11
    assert grid["levels"][0] == pytest.approx(grid["lower_bound"])
    assert grid["levels"][-1] == pytest.approx(grid["upper_bound"])


def test_grid_width_is_at_least_six_atr():
    highs, lows, closes = make_candles()

    grid = build_adaptive_grid(highs, lows, closes)

    width = grid["upper_bound"] - grid["lower_bound"]

    assert width >= 6 * grid["atr"]


def test_rejects_insufficient_lookback():
    highs, lows, closes = make_candles(count=20)

    with pytest.raises(ValueError):
        build_adaptive_grid(highs, lows, closes, lookback=72)


def test_rejects_mismatched_candle_lengths():
    highs, lows, closes = make_candles()

    with pytest.raises(ValueError):
        build_adaptive_grid(highs, lows[:-1], closes)


def test_rejects_invalid_boundary_multiplier():
    highs, lows, closes = make_candles()

    with pytest.raises(ValueError):
        build_adaptive_grid(
            highs,
            lows,
            closes,
            boundary_atr_multiplier=-0.5,
        )



def test_rejects_grid_wider_than_maximum():
    highs, lows, closes = make_candles(count=80)

    # Keep the minimum valid while setting a tight maximum.
    with pytest.raises(ValueError, match="exceeds maximum"):
        build_adaptive_grid(
            highs,
            lows,
            closes,
            minimum_range_atr=1.0,
            maximum_range_atr=5.0,
        )



def test_rejects_minimum_width_above_maximum():
    highs, lows, closes = make_candles(count=80)

    with pytest.raises(ValueError, match="cannot exceed"):
        build_adaptive_grid(
            highs,
            lows,
            closes,
            minimum_range_atr=10.0,
            maximum_range_atr=5.0,
        )


def test_rejects_close_outside_candle_range():
    highs, lows, closes = make_candles(count=80)
    closes[-1] = highs[-1] + 10

    with pytest.raises(ValueError, match="between its low and high"):
        build_adaptive_grid(highs, lows, closes)


def test_rejects_non_finite_candle_price():
    highs, lows, closes = make_candles(count=80)
    highs[-1] = float("nan")

    with pytest.raises(ValueError, match="finite numbers"):
        build_adaptive_grid(highs, lows, closes)

