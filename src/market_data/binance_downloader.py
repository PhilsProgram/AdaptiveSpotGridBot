
import csv
from datetime import datetime, timezone
from pathlib import Path

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_FILE = DATA_DIR / "btc_usdt_1h.csv"

API_URL = "https://data-api.binance.vision/api/v3/klines"


def download_candles() -> None:
    """Download recent BTC/USDT hourly candles and save them to CSV."""

    params = {
        "symbol": "BTCUSDT",
        "interval": "1h",
        "limit": 200,
    }

    print("Requesting public BTC/USDT hourly candle data...")

    try:
        response = requests.get(
            API_URL,
            params=params,
            timeout=20,
        )
        response.raise_for_status()
        raw_candles = response.json()

    except requests.RequestException as exc:
        print(f"Download failed: {exc}")
        return

    if not isinstance(raw_candles, list) or not raw_candles:
        print("No candle data was returned.")
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open(
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

        for candle in raw_candles:
            timestamp = datetime.fromtimestamp(
                candle[0] / 1000,
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

    print(f"Download complete: {len(raw_candles)} candles saved.")
    print(f"File location: {OUTPUT_FILE}")


if __name__ == "__main__":
    download_candles()
