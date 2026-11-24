import json
import math
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "strategy.json"


def load_config(config_path: str | Path | None = None) -> dict:
    """Load and validate the bot's strategy configuration."""
    
    if config_path is None:
        config_path = CONFIG_FILE

    config_path = Path(config_path)

    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path

    if not config_path.is_file():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}"
        )

    with config_path.open("r", encoding="utf-8") as file:
            config = json.load(file)

    required_keys = {
        "symbol",
        "timeframe",
        "starting_quote_balance",
        "initial_quote_allocation",
        "initial_base_allocation",
        "atr_period",
        "lookback_candles",
        "grid_intervals",
        "boundary_atr_multiplier",
        "minimum_range_atr",
        "maximum_range_atr",
        "drawdown_pause_fraction",
        "fee_rate",
    }

    missing_keys = required_keys - config.keys()

    if missing_keys:
        raise ValueError(
            f"Missing configuration settings: {sorted(missing_keys)}"
        )

    if not isinstance(config["symbol"], str) or not config["symbol"].strip():
        raise ValueError("symbol must be a non-empty string")

    if not isinstance(config["timeframe"], str) or not config["timeframe"].strip():
        raise ValueError("timeframe must be a non-empty string")

    numeric_keys = required_keys - {"symbol", "timeframe"}

    for key in numeric_keys:
        value = config[key]

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{key} must be a number")

        if not math.isfinite(value):
            raise ValueError(f"{key} must be finite")

    if config["starting_quote_balance"] <= 0:
        raise ValueError("starting_quote_balance must be positive")

    for key in ("initial_quote_allocation", "initial_base_allocation"):
        if not 0 <= config[key] <= 1:
            raise ValueError(f"{key} must be between 0 and 1")

    if not math.isclose(
        config["initial_quote_allocation"]
        + config["initial_base_allocation"],
        1.0,
        abs_tol=1e-9,
    ):
        raise ValueError("Initial allocations must add up to 1")

    for key in ("atr_period", "lookback_candles", "grid_intervals"):
        if isinstance(config[key], bool) or not isinstance(config[key], int):
            raise ValueError(f"{key} must be an integer")

        if config[key] < 1:
            raise ValueError(f"{key} must be at least 1")

    if config["lookback_candles"] < config["atr_period"]:
        raise ValueError("lookback_candles must be >= atr_period")

    if config["boundary_atr_multiplier"] < 0:
        raise ValueError("boundary_atr_multiplier cannot be negative")

    if config["minimum_range_atr"] <= 0:
        raise ValueError("minimum_range_atr must be positive")

    if config["maximum_range_atr"] < config["minimum_range_atr"]:
        raise ValueError(
            "maximum_range_atr must be >= minimum_range_atr"
        )

    if not 0 < config["drawdown_pause_fraction"] < 1:
        raise ValueError("drawdown_pause_fraction must be between 0 and 1")
    
    if not 0 <= config["fee_rate"] < 1:
        raise ValueError(
            "fee_rate must be between 0 (inclusive) and 1 (exclusive)"
    )

    return config
