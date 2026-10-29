import csv
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

OUTPUT_FILE = DATA_DIR / "btc_usdt_1h_90d.csv"

API_URL = "https://data-api.binance.vision/api/v3/klines"

SYMBOL = "BTCUSDT"
INTERVAL = "1h"

CANDLE_DURATION_MS = 60 * 60 * 1000
REQUEST_LIMIT = 1000
DAYS_TO_DOWNLOAD = 90


def download_historical_candles() -> None:
    """Download completed hourly BTC/USDT candles for the last 90 days."""

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=DAYS_TO_DOWNLOAD)

    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)

    all_candles = {}
    current_start_ms = start_ms

    print(f"Downloading {DAYS_TO_DOWNLOAD} days of BTC/USDT hourly data...")

    try:
        with requests.Session() as session:

            while current_start_ms < end_ms:

                params = {
                    "symbol": SYMBOL,
                    "interval": INTERVAL,
                    "startTime": current_start_ms,
                    "endTime": end_ms,
                    "limit": REQUEST_LIMIT,
                }

                response = session.get(
                    API_URL,
                    params=params,
                    timeout=30,
                )

                response.raise_for_status()
                batch = response.json()

                if not isinstance(batch, list):
                    raise ValueError("Binance returned an unexpected response")

                if not batch:
                    break

                for candle in batch:
                    if not isinstance(candle, list) or len(candle) < 6:
                        raise ValueError("Binance returned an invalid candle")

                    open_time = int(candle[0])

                    # Keep only candles inside our requested date range.
                    if start_ms <= open_time < end_ms:
                        all_candles[open_time] = candle

                last_open_time = int(batch[-1][0])

                # Move forward by one millisecond to avoid duplicates.
                next_start_ms = last_open_time + 1

                if next_start_ms <= current_start_ms:
                    raise ValueError("Download pagination did not advance")

                current_start_ms = next_start_ms

                print(f"Collected {len(all_candles)} candles so far...")

                if len(batch) < REQUEST_LIMIT:
                    break

                time.sleep(0.2)

    except (requests.RequestException, ValueError, TypeError, IndexError) as exc:
        print(f"Download failed: {exc}")
        print("The historical CSV file was not updated.")
        return

    # Sort candles by their opening timestamps.
    sorted_candles = sorted(
        all_candles.values(),
        key=lambda candle: int(candle[0]),
    )

    # Remove the current unfinished hourly candle.
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    completed_candles = [
        candle
        for candle in sorted_candles
        if int(candle[0]) + CANDLE_DURATION_MS <= now_ms
    ]

    if not completed_candles:
        print("No completed candles were downloaded.")
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Write to a temporary file first, so an interrupted download
    # cannot leave a partially written historical CSV.
    temporary_file = OUTPUT_FILE.with_suffix(".tmp")

    try:
        with temporary_file.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ])

            for candle in completed_candles:
                timestamp = datetime.fromtimestamp(
                    int(candle[0]) / 1000,
                    tz=timezone.utc,
                )

                writer.writerow([
                    timestamp.isoformat(),
                    candle[1],
                    candle[2],
                    candle[3],
                    candle[4],
                    candle[5],
                ])

        # Replace the destination only after the new file is complete.
        temporary_file.replace(OUTPUT_FILE)

    except OSError as exc:
        print(f"Could not save historical data: {exc}")

        if temporary_file.exists():
            temporary_file.unlink()

        return

    print("\nHistorical download complete!")
    print(f"Total completed candles: {len(completed_candles)}")
    print(f"First candle: {completed_candles[0][0]}")
    print(f"Last candle: {completed_candles[-1][0]}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    download_historical_candles()
