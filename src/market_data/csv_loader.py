import csv
import math
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_COLUMNS = {
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
}


def load_candles(csv_path: str | Path) -> list[dict]:
    """Load and validate chronological hourly OHLCV candles from CSV."""

    path = Path(csv_path)

    if not path.is_file():
        raise FileNotFoundError(f"Candle CSV file not found: {path}")

    candles = []

    with path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError("CSV file is empty or missing its header")

        reader.fieldnames = [name.strip() for name in reader.fieldnames]

        missing = REQUIRED_COLUMNS - set(reader.fieldnames)

        if missing:
            raise ValueError(
                f"CSV is missing required columns: {sorted(missing)}"
            )

        for row_number, row in enumerate(reader, start=2):
            try:
                timestamp_text = row["timestamp"].strip()
                timestamp = datetime.fromisoformat(
                    timestamp_text.replace("Z", "+00:00")
                )

                if timestamp.tzinfo is None:
                    raise ValueError("timestamp must include a timezone")

                timestamp = timestamp.astimezone(timezone.utc)

                open_price = float(row["open"])
                high = float(row["high"])
                low = float(row["low"])
                close = float(row["close"])
                volume = float(row["volume"])

            except (AttributeError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid data on CSV row {row_number}: {exc}"
                ) from exc

            values = (open_price, high, low, close, volume)

            if not all(math.isfinite(value) for value in values):
                raise ValueError(
                    f"Non-finite number on CSV row {row_number}"
                )

            if min(open_price, high, low, close) <= 0:
                raise ValueError(
                    f"Prices must be positive on CSV row {row_number}"
                )

            if volume < 0:
                raise ValueError(
                    f"Volume cannot be negative on CSV row {row_number}"
                )

            if high < max(open_price, close, low):
                raise ValueError(
                    f"High is inconsistent with OHLC prices "
                    f"on CSV row {row_number}"
                )

            if low > min(open_price, close, high):
                raise ValueError(
                    f"Low is inconsistent with OHLC prices "
                    f"on CSV row {row_number}"
                )

            if candles:
                previous_timestamp = candles[-1]["timestamp"]

                if timestamp <= previous_timestamp:
                    raise ValueError(
                        "Timestamps must be strictly increasing; "
                        f"check CSV row {row_number}"
                    )

                elapsed = timestamp - previous_timestamp

                if elapsed.total_seconds() != 3600:
                    raise ValueError(
                        "Expected candles exactly one hour apart; "
                        f"check CSV row {row_number}"
                    )

            candles.append(
                {
                    "timestamp": timestamp,
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume,
                }
            )

    if not candles:
        raise ValueError("CSV contains no candle data")

    return candles


def filter_completed_candles(candles: list[dict]) -> list[dict]:
    """Keep only hourly candles whose closing time has passed."""

    now = datetime.now(timezone.utc)

    return [
        candle
        for candle in candles
        if (candle["timestamp"].timestamp() + 3600) <= now.timestamp()
    ]
