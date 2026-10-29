
import pytest

from src.strategy.volatility import calculate_atr


def test_atr_for_simple_candles():
    highs = [105, 108, 107]
    lows = [100, 102, 103]
    closes = [103, 106, 104]

    # True ranges: 5, 6, 4
    assert calculate_atr(highs, lows, closes, period=3) == pytest.approx(5)


def test_atr_accounts_for_gaps():
    highs = [105, 112]
    lows = [100, 109]
    closes = [103, 110]

    # True ranges: 5, 9 (112 - previous close of 103)
    assert calculate_atr(highs, lows, closes, period=2) == pytest.approx(7)


def test_rejects_insufficient_candles():
    with pytest.raises(ValueError):
        calculate_atr([105], [100], [103], period=14)


def test_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        calculate_atr([105, 108], [100], [103, 106], period=2)


def test_rejects_invalid_prices():
    with pytest.raises(ValueError):
        calculate_atr([105], [106], [103], period=1)


def test_rejects_invalid_period():
    with pytest.raises(ValueError):
        calculate_atr([105], [100], [103], period=0)
