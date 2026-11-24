
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

def test_fee_rate_is_loaded():
    config = load_config()

    assert config["fee_rate"] == pytest.approx(0.001)


def test_zero_fee_rate_is_allowed(tmp_path, monkeypatch):
    config = config_loader.load_config()
    config["fee_rate"] = 0.0

    config_file = tmp_path / "strategy.json"
    config_file.write_text(json.dumps(config), encoding="utf-8")

    monkeypatch.setattr(config_loader, "CONFIG_FILE", config_file)

    loaded_config = config_loader.load_config()

    assert loaded_config["fee_rate"] == 0.0


@pytest.mark.parametrize("fee_rate", [-0.001, 1.0, 1.5])
def test_rejects_invalid_fee_rates(tmp_path, monkeypatch, fee_rate):
    config = config_loader.load_config()
    config["fee_rate"] = fee_rate

    config_file = tmp_path / "strategy.json"
    config_file.write_text(json.dumps(config), encoding="utf-8")

    monkeypatch.setattr(config_loader, "CONFIG_FILE", config_file)

    with pytest.raises(ValueError, match="fee_rate"):
        config_loader.load_config()