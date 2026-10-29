
from src.market_data.csv_loader import (
    load_candles,
    filter_completed_candles,
)


def prepare_historical_data(
    csv_path: str,
    minimum_candles: int = 72,
) -> list[dict]:
    """Load, validate, and prepare completed candles for backtesting."""

    if (
        isinstance(minimum_candles, bool)
        or not isinstance(minimum_candles, int)
        or minimum_candles < 1
    ):
        raise ValueError("minimum_candles must be a positive integer")

    # Load and validate the original CSV data.
    candles = load_candles(csv_path)

    # Remove candles that have not finished yet.
    completed_candles = filter_completed_candles(candles)

    # Ensure sufficient historical data remains.
    if len(completed_candles) < minimum_candles:
        raise ValueError(
            f"Not enough completed candles. "
            f"Required: {minimum_candles}, "
            f"available: {len(completed_candles)}"
        )

    return completed_candles
