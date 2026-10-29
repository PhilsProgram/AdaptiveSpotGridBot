
import pytest

from src.config_loader import load_config

import json 

from src import config_loader


def test_loads_strategy_config():
    config = load_config()

    assert config["symbol"] == "BTC/USDT"
    assert config["timeframe"] == "1h"
    assert config["starting_quote_balance"] == 1000.0
    assert config["atr_period"] == 14
    assert config["lookback_candles"] == 72
    assert config["grid_intervals"] == 10


def test_initial_allocations_add_up_to_one():
    config = load_config()

    total = (
        config["initial_quote_allocation"]
        + config["initial_base_allocation"]
    )

    assert total == pytest.approx(1.0)


def test_drawdown_pause_is_ten_percent():
    config = load_config()

    assert config["drawdown_pause_fraction"] == pytest.approx(0.10)



def test_rejects_allocations_that_do_not_add_up(tmp_path, monkeypatch):
    config = config_loader.load_config()
    config["initial_quote_allocation"] = 0.8
    config["initial_base_allocation"] = 0.8

    config_file = tmp_path / "strategy.json"
    config_file.write_text(json.dumps(config), encoding="utf-8")

    monkeypatch.setattr(config_loader, "CONFIG_FILE", config_file)

    with pytest.raises(ValueError, match="allocations must add up"):
        config_loader.load_config()


def test_rejects_negative_starting_balance(tmp_path, monkeypatch):
    config = config_loader.load_config()
    config["starting_quote_balance"] = -100

    config_file = tmp_path / "strategy.json"
    config_file.write_text(json.dumps(config), encoding="utf-8")

    monkeypatch.setattr(config_loader, "CONFIG_FILE", config_file)

    with pytest.raises(ValueError, match="must be positive"):
        config_loader.load_config()


def test_rejects_maximum_range_below_minimum(tmp_path, monkeypatch):
    config = config_loader.load_config()
    config["minimum_range_atr"] = 10
    config["maximum_range_atr"] = 5

    config_file = tmp_path / "strategy.json"
    config_file.write_text(json.dumps(config), encoding="utf-8")

    monkeypatch.setattr(config_loader, "CONFIG_FILE", config_file)

    with pytest.raises(ValueError, match="maximum_range_atr"):
        config_loader.load_config()
