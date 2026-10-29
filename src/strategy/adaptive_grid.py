
import math


def calculate_grid_levels(
    lower: float,
    upper: float,
    intervals: int = 10,
) -> list[float]:
    """Calculate equally percentage-spaced price levels."""

    if not math.isfinite(lower) or not math.isfinite(upper):
        raise ValueError("Grid boundaries must be finite numbers.")

    if lower <= 0:
        raise ValueError("The lower boundary must be greater than zero.")

    if upper <= lower:
        raise ValueError("The upper boundary must be greater than the lower boundary.")

    if isinstance(intervals, bool) or not isinstance(intervals, int):
        raise ValueError("Intervals must be an integer.")

    if intervals < 1:
        raise ValueError("Intervals must be at least 1.")

    ratio = upper / lower

    levels = [
        lower * (ratio ** (i / intervals))
        for i in range(intervals + 1)
    ]

    # Preserve the exact boundaries.
    levels[0] = lower
    levels[-1] = upper

    return levels