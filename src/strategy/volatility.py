
import math


def calculate_atr(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 14,
) -> float:
    """Calculate ATR using the simple average of the latest true ranges.

    Each input must contain the same number of chronological candles.
    The first candle's true range is its high minus its low.
    """

    if isinstance(period, bool) or not isinstance(period, int) or period < 1:
        raise ValueError("period must be a positive integer")

    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("highs, lows, and closes must have equal lengths")

    if len(highs) < period:
        raise ValueError("Not enough candles for the requested ATR period")

    for high, low, close in zip(highs, lows, closes):
        if not all(math.isfinite(value) for value in (high, low, close)):
            raise ValueError("Candle values must be finite numbers")

        if low <= 0 or close <= 0 or high < low:
            raise ValueError("Candle prices must be positive and high >= low")

    true_ranges = []

    for i, (high, low, close) in enumerate(zip(highs, lows, closes)):
        if i == 0:
            true_range = high - low
        else:
            previous_close = closes[i - 1]
            true_range = max(
                high - low,
                abs(high - previous_close),
                abs(low - previous_close),
            )

        true_ranges.append(true_range)

    return sum(true_ranges[-period:]) / period
