
import math

from src.strategy.adaptive_grid import calculate_grid_levels
from src.strategy.volatility import calculate_atr

class GridRejectedError(ValueError):
    """Raised when a calculated grid fails a strategy safety limit."""


def build_adaptive_grid(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    atr_period: int = 14,
    lookback: int = 72,
    intervals: int = 10,
    boundary_atr_multiplier: float = 0.5,
    minimum_range_atr: float = 6.0,
    maximum_range_atr: float = 20.0,
) -> dict:
    """Build a volatility-adaptive grid from completed candles.

    Reject unsafe or invalid ranges instead of silently forcing
    the grid into an unsuitable price range.
    """

    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("highs, lows, and closes must have equal lengths")

    if isinstance(lookback, bool) or not isinstance(lookback, int) or lookback < 1:
        raise ValueError("lookback must be a positive integer")

    if len(closes) < lookback:
        raise ValueError("Not enough candles for the requested lookback")

    if (
        not math.isfinite(boundary_atr_multiplier)
        or boundary_atr_multiplier < 0
    ):
        raise ValueError(
            "boundary_atr_multiplier must be finite and non-negative"
        )

    if not math.isfinite(minimum_range_atr) or minimum_range_atr <= 0:
        raise ValueError("minimum_range_atr must be finite and positive")

    if not math.isfinite(maximum_range_atr) or maximum_range_atr <= 0:
        raise ValueError("maximum_range_atr must be finite and positive")

    if minimum_range_atr > maximum_range_atr:
        raise ValueError(
            "minimum_range_atr cannot exceed maximum_range_atr"
        )

    # Validate every candle before using its prices.
    for high, low, close in zip(highs, lows, closes):
        if not all(
            math.isfinite(value) for value in (high, low, close)
        ):
            raise ValueError("Candle prices must be finite numbers")

        if low <= 0 or high < low:
            raise ValueError("Candle prices must be positive and high >= low")

        if not low <= close <= high:
            raise ValueError("Each close must be between its low and high")

    atr = calculate_atr(
        highs,
        lows,
        closes,
        period=atr_period,
    )

    if atr <= 0:
        raise ValueError("ATR must be positive to build an adaptive grid")

    recent_high = max(highs[-lookback:])
    recent_low = min(lows[-lookback:])

    lower_bound = recent_low - boundary_atr_multiplier * atr
    upper_bound = recent_high + boundary_atr_multiplier * atr

    midpoint = (lower_bound + upper_bound) / 2
    minimum_width = minimum_range_atr * atr
    maximum_width = maximum_range_atr * atr
    current_width = upper_bound - lower_bound

    # Expand narrow ranges, but never silently shrink wide ranges.
    if current_width < minimum_width:
        lower_bound = midpoint - minimum_width / 2
        upper_bound = midpoint + minimum_width / 2

    final_width = upper_bound - lower_bound

    if final_width > maximum_width:
        raise GridRejectedError(
            "Calculated grid exceeds maximum permitted width; "
            "grid generation rejected"
    )

    levels = calculate_grid_levels(
        lower_bound,
        upper_bound,
        intervals=intervals,
    )

    return {
        "atr": atr,
        "recent_high": recent_high,
        "recent_low": recent_low,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
        "levels": levels,
    }
