from decimal import Decimal

from src.execution.balance_manager import VirtualBalanceManager
from src.backtesting.paper_trader import (
    calculate_portfolio_equity,
    cancel_open_orders,
)
from unittest.mock import patch
from datetime import datetime


def test_calculate_portfolio_equity_includes_reserved_balances():
    manager = VirtualBalanceManager(
        available_quote=Decimal("500"),
        available_base=Decimal("5"),
    )

    buy_order = {
        "order_id": "BUY-1",
        "side": "buy",
        "price": Decimal("10"),
        "quantity": Decimal("2"),
        "status": "open",
    }

    sell_order = {
        "order_id": "SELL-1",
        "side": "sell",
        "price": Decimal("10000"),
        "quantity": Decimal("0.002"),
        "status": "open",
    }

    manager.reserve_order(buy_order)
    manager.reserve_order(sell_order)

    equity = calculate_portfolio_equity(
        manager,
        Decimal("10000"),
    )

    assert equity == Decimal("50500")


def test_cancel_open_orders_releases_reservations():
    manager = VirtualBalanceManager(
        available_quote=Decimal("100"),
        available_base=Decimal("0.01"),
    )

    buy_order = {
        "order_id": "BUY-1",
        "side": "buy",
        "price": Decimal("10"),
        "quantity": Decimal("2"),
        "status": "open",
    }

    sell_order = {
        "order_id": "SELL-1",
        "side": "sell",
        "price": Decimal("20"),
        "quantity": Decimal("0.005"),
        "status": "open",
    }

    manager.reserve_order(buy_order)
    manager.reserve_order(sell_order)

    manager.fill_order(sell_order)

    cancelled = cancel_open_orders(
        [buy_order, sell_order],
        manager,
    )

    assert cancelled == 1
    assert buy_order["status"] == "cancelled"
    assert sell_order["status"] == "filled"

    assert manager.reserved_quote == Decimal("0")
    assert manager.reserved_base == Decimal("0")
    assert manager.available_quote == Decimal("100.1")
    assert manager.available_base == Decimal("0.005")
    
def test_initialize_paper_trader_creates_initial_grid_and_orders():
    from src.backtesting.paper_trader import initialize_paper_trader

    state = initialize_paper_trader(
        csv_path="data/btc_usdt_1h_90d.csv",
        config_path="config/strategy.json",
    )

    # Initial grid
    assert state["active_grid_id"] == "G001"
    assert len(state["active_grid_levels"]) == 11

    # Initial orders
    assert len(state["active_orders"]) > 0
    assert len(state["all_orders"]) == len(state["active_orders"])

    order_ids = [
        order["order_id"]
        for order in state["active_orders"]
    ]

    assert len(order_ids) == len(set(order_ids))

    for order in state["active_orders"]:
        assert order["status"] == "open"
        assert "G001" in order["order_id"]

    # Initial portfolio
    assert state["starting_equity"] == Decimal("1000")
    assert state["initial_equity"] <= state["starting_equity"]
    assert (
        state["starting_equity"] - state["initial_equity"]
    ) < Decimal("0.01")

    # Historical data warm-up
    assert len(state["candles"]) > state["lookback"]
    assert state["initial_price"] > 0

    # Both quote and base funds should be reserved for open orders.
    manager = state["balance_manager"]

    assert manager.reserved_quote > 0
    assert manager.reserved_base > 0
    
def test_unchanged_grid_preserves_existing_orders_and_reservations():
    from src.backtesting.paper_trader import run_paper_trading_simulation

    # Create a controlled initial grid.
    initial_levels = tuple(
        Decimal(str(price))
        for price in [
            90, 92, 94, 96, 98, 100,
            102, 104, 106, 108, 110,
        ]
    )

    fake_candles = [
        {
            "timestamp": __import__("datetime").datetime(
                2026, 1, 1, hour, tzinfo=__import__("datetime").timezone.utc
            ),
            "open": 100.0,
            "high": 100.5,
            "low": 99.5,
            "close": 100.0,
            "volume": 1.0,
        }
        for hour in range(3)
    ]

    fake_config = {
        "starting_quote_balance": 1000.0,
        "drawdown_pause_fraction": 0.10,
        "atr_period": 14,
        "grid_intervals": 10,
        "boundary_atr_multiplier": 0.5,
        "minimum_range_atr": 6.0,
        "maximum_range_atr": 20.0,
    }

    fake_orders = [
        {
            "order_id": f"BUY-G001-{i}",
            "side": "buy",
            "price": Decimal(str(90 + i)),
            "quantity": Decimal("1"),
            "status": "open",
        }
        for i in range(1, 6)
    ]

    fake_orders += [
        {
            "order_id": f"SELL-G001-{i}",
            "side": "sell",
            "price": Decimal(str(105 + i)),
            "quantity": Decimal("0.001"),
            "status": "open",
        }
        for i in range(1, 6)
    ]

    manager = VirtualBalanceManager(
        available_quote=Decimal("500"),
        available_base=Decimal("5"),
    )

    for order in fake_orders:
        amount = (
            order["price"] * order["quantity"]
            if order["side"] == "buy"
            else order["quantity"]
        )

        manager.reserve_order(order)

    fake_state = {
        "config": fake_config,
        "candles": fake_candles,
        "lookback": 2,
        "initial_price": Decimal("100"),
        "initial_timestamp": fake_candles[1]["timestamp"].isoformat(),
        "starting_equity": Decimal("1000"),
        "initial_equity": Decimal("1000"),
        "balance_manager": manager,
        "active_grid": {"levels": list(initial_levels)},
        "active_grid_id": "G001",
        "active_grid_levels": initial_levels,
        "active_orders": fake_orders,
        "all_orders": list(fake_orders),
        "next_grid_number": 2,
    }

    fake_grid = {
        "levels": [float(level) for level in initial_levels],
    }

    with (
        patch(
            "src.backtesting.paper_trader.initialize_paper_trader",
            return_value=fake_state,
        ),
        patch(
            "src.backtesting.paper_trader.build_adaptive_grid",
            return_value=fake_grid,
        ),
        patch(
            "src.backtesting.paper_trader.execute_candle_orders",
            return_value=[],
        ) as execute_mock,
    ):
        result = run_paper_trading_simulation()

    assert execute_mock.call_count == 1

    assert len(result["all_orders"]) == 10

    assert all(
        order["status"] == "open"
        for order in result["all_orders"]
    )

    assert result["all_orders"] == fake_orders

    assert result["final_balances"]["reserved_quote"] == manager.reserved_quote
    assert result["final_balances"]["reserved_base"] == manager.reserved_base

    assert result["equity_history"][0]["active_orders"] == 10
    assert result["equity_history"][0]["grid_active"] is True
    

def test_changed_grid_cancels_old_orders_and_creates_new_orders():
    from src.backtesting.paper_trader import run_paper_trading_simulation

    initial_levels = tuple(
        Decimal(str(price))
        for price in range(90, 111, 2)
    )

    new_levels = tuple(
        Decimal(str(price))
        for price in range(92, 113, 2)
    )

    fake_candles = [
        {
            "timestamp": __import__("datetime").datetime(
                2026, 1, 1, hour,
                tzinfo=__import__("datetime").timezone.utc
            ),
            "open": 100.0,
            "high": 100.5,
            "low": 99.5,
            "close": 100.0,
            "volume": 1.0,
        }
        for hour in range(3)
    ]

    fake_config = {
        "starting_quote_balance": 1000.0,
        "drawdown_pause_fraction": 0.10,
        "atr_period": 14,
        "grid_intervals": 10,
        "boundary_atr_multiplier": 0.5,
        "minimum_range_atr": 6.0,
        "maximum_range_atr": 20.0,
    }

    manager = VirtualBalanceManager(
        available_quote=Decimal("500"),
        available_base=Decimal("5"),
    )

    old_orders = []

    for i, price in enumerate(range(91, 96), start=1):
        old_orders.append({
            "order_id": f"BUY-G001-{i}",
            "side": "buy",
            "price": Decimal(str(price)),
            "quantity": Decimal("1"),
            "status": "open",
        })

    for i, price in enumerate(range(106, 111), start=1):
        old_orders.append({
            "order_id": f"SELL-G001-{i}",
            "side": "sell",
            "price": Decimal(str(price)),
            "quantity": Decimal("0.001"),
            "status": "open",
        })

    for order in old_orders:
        manager.reserve_order(order)

    fake_state = {
        "config": fake_config,
        "candles": fake_candles,
        "lookback": 2,
        "initial_price": Decimal("100"),
        "initial_timestamp": fake_candles[1]["timestamp"].isoformat(),
        "starting_equity": Decimal("1000"),
        "initial_equity": Decimal("1000"),
        "balance_manager": manager,
        "active_grid": {"levels": list(initial_levels)},
        "active_grid_id": "G001",
        "active_grid_levels": initial_levels,
        "active_orders": old_orders,
        "all_orders": list(old_orders),
        "next_grid_number": 2,
    }

    fake_grid = {
        "levels": list(new_levels),
    }

    with (
        patch(
            "src.backtesting.paper_trader.initialize_paper_trader",
            return_value=fake_state,
        ),
        patch(
            "src.backtesting.paper_trader.build_adaptive_grid",
            return_value=fake_grid,
        ),
        patch(
            "src.backtesting.paper_trader.execute_candle_orders",
            return_value=[],
        ),
    ):
        result = run_paper_trading_simulation()

    # All old orders must be cancelled.
    assert all(
        order["status"] == "cancelled"
        for order in old_orders
    )

    # New orders must have been created.
    new_orders = [
        order for order in result["all_orders"]
        if order["order_id"].startswith(("BUY-G002-", "SELL-G002-"))
    ]

    assert len(new_orders) > 0

    # New orders must remain open.
    assert all(
        order["status"] == "open"
        for order in new_orders
    )

    # The active grid must now be G002.
    assert result["grid_history"][-1]["grid_id"] == "G002"

    # Old reservations must have been released.
    assert all(
        order["order_id"] not in manager._reservations
        for order in old_orders
    )

    # New orders must have reservations.
    assert all(
        order["order_id"] in manager._reservations
        for order in new_orders
    )


def test_rejected_grid_cancels_orders_and_releases_reservations():
    from src.backtesting.paper_trader import run_paper_trading_simulation
    from src.strategy.grid_builder import GridRejectedError

    initial_levels = tuple(
        Decimal(str(price))
        for price in range(90, 111, 2)
    )

    fake_candles = [
        {
            "timestamp": __import__("datetime").datetime(
                2026, 1, 1, hour,
                tzinfo=__import__("datetime").timezone.utc
            ),
            "open": 100.0,
            "high": 100.5,
            "low": 99.5,
            "close": 100.0,
            "volume": 1.0,
        }
        for hour in range(3)
    ]

    fake_config = {
        "starting_quote_balance": 1000.0,
        "drawdown_pause_fraction": 0.10,
        "atr_period": 14,
        "grid_intervals": 10,
        "boundary_atr_multiplier": 0.5,
        "minimum_range_atr": 6.0,
        "maximum_range_atr": 20.0,
    }

    manager = VirtualBalanceManager(
        available_quote=Decimal("500"),
        available_base=Decimal("5"),
    )

    old_orders = []

    for i, price in enumerate(range(91, 96), start=1):
        old_orders.append({
            "order_id": f"BUY-G001-{i}",
            "side": "buy",
            "price": Decimal(str(price)),
            "quantity": Decimal("1"),
            "status": "open",
        })

    for i, price in enumerate(range(106, 111), start=1):
        old_orders.append({
            "order_id": f"SELL-G001-{i}",
            "side": "sell",
            "price": Decimal(str(price)),
            "quantity": Decimal("0.001"),
            "status": "open",
        })

    for order in old_orders:
        manager.reserve_order(order)

    fake_state = {
        "config": fake_config,
        "candles": fake_candles,
        "lookback": 2,
        "initial_price": Decimal("100"),
        "initial_timestamp": fake_candles[1]["timestamp"].isoformat(),
        "starting_equity": Decimal("1000"),
        "initial_equity": Decimal("1000"),
        "balance_manager": manager,
        "active_grid": {"levels": list(initial_levels)},
        "active_grid_id": "G001",
        "active_grid_levels": initial_levels,
        "active_orders": old_orders,
        "all_orders": list(old_orders),
        "next_grid_number": 2,
    }

    with (
        patch(
            "src.backtesting.paper_trader.initialize_paper_trader",
            return_value=fake_state,
        ),
        patch(
            "src.backtesting.paper_trader.build_adaptive_grid",
            side_effect=GridRejectedError("Test grid rejection"),
        ),
        patch(
            "src.backtesting.paper_trader.execute_candle_orders",
            return_value=[],
        ),
    ):
        result = run_paper_trading_simulation()

    # Every old order must be cancelled.
    assert all(
        order["status"] == "cancelled"
        for order in old_orders
    )

    # No replacement orders may have been created.
    assert len(result["all_orders"]) == len(old_orders)

    # There must be no remaining open orders.
    assert not any(
        order["status"] == "open"
        for order in result["all_orders"]
    )

    # Every old reservation must have been released.
    assert manager.reserved_quote == Decimal("0")
    assert manager.reserved_base == Decimal("0")
    assert not manager._reservations

    # The rejected calculation must be recorded.
    assert len(result["rejected_grids"]) == 1
    

def test_bot_recovers_after_rejected_grids():
    from src.backtesting.paper_trader import run_paper_trading_simulation
    from src.strategy.grid_builder import GridRejectedError

    initial_levels = tuple(
        Decimal(str(price))
        for price in range(90, 111, 2)
    )

    new_levels = tuple(
        Decimal(str(price))
        for price in range(92, 113, 2)
    )

    fake_candles = [
        {
            "timestamp": __import__("datetime").datetime(
                2026, 1, 1, hour,
                tzinfo=__import__("datetime").timezone.utc
            ),
            "open": 100.0,
            "high": 100.5,
            "low": 99.5,
            "close": 100.0,
            "volume": 1.0,
        }
        for hour in range(5)
    ]

    fake_config = {
        "starting_quote_balance": 1000.0,
        "drawdown_pause_fraction": 0.10,
        "atr_period": 14,
        "grid_intervals": 10,
        "boundary_atr_multiplier": 0.5,
        "minimum_range_atr": 6.0,
        "maximum_range_atr": 20.0,
    }

    manager = VirtualBalanceManager(
        available_quote=Decimal("500"),
        available_base=Decimal("5"),
    )

    old_orders = []

    for i, price in enumerate(range(91, 96), start=1):
        old_orders.append({
            "order_id": f"BUY-G001-{i}",
            "side": "buy",
            "price": Decimal(str(price)),
            "quantity": Decimal("1"),
            "status": "open",
        })

    for i, price in enumerate(range(106, 111), start=1):
        old_orders.append({
            "order_id": f"SELL-G001-{i}",
            "side": "sell",
            "price": Decimal(str(price)),
            "quantity": Decimal("0.001"),
            "status": "open",
        })

    for order in old_orders:
        manager.reserve_order(order)

    fake_state = {
        "config": fake_config,
        "candles": fake_candles,
        "lookback": 2,
        "initial_price": Decimal("100"),
        "initial_timestamp": fake_candles[1]["timestamp"].isoformat(),
        "starting_equity": Decimal("1000"),
        "initial_equity": Decimal("1000"),
        "balance_manager": manager,
        "active_grid": {"levels": list(initial_levels)},
        "active_grid_id": "G001",
        "active_grid_levels": initial_levels,
        "active_orders": old_orders,
        "all_orders": list(old_orders),
        "next_grid_number": 2,
    }

    valid_grid = {
        "levels": list(new_levels),
    }

    with (
        patch(
            "src.backtesting.paper_trader.initialize_paper_trader",
            return_value=fake_state,
        ),
        patch(
            "src.backtesting.paper_trader.build_adaptive_grid",
            side_effect=[
                GridRejectedError("First rejection"),
                GridRejectedError("Second rejection"),
                valid_grid,
            ],
        ),
        patch(
            "src.backtesting.paper_trader.execute_candle_orders",
            return_value=[],
        ),
    ):
        result = run_paper_trading_simulation()

    # The first two calculations must be rejected.
    assert len(result["rejected_grids"]) == 2

    # The original orders must have been cancelled.
    assert all(
        order["status"] == "cancelled"
        for order in old_orders
    )

    # The third calculation must successfully activate G002.
    assert result["grid_history"][-1]["grid_id"] == "G002"

    # Only one valid grid calculation should be recorded.
    assert len(result["grid_history"]) == 1

    # New G002 orders must have been created.
    new_orders = [
        order for order in result["all_orders"]
        if order["order_id"].startswith(("BUY-G002-", "SELL-G002-"))
    ]

    assert len(new_orders) > 0

    assert all(
        order["status"] == "open"
        for order in new_orders
    )

    # New orders must have reservations.
    assert all(
        order["order_id"] in manager._reservations
        for order in new_orders
    )

    # The bot must be active again.
    assert result["equity_history"][-1]["grid_active"] is True
    assert result["equity_history"][-1]["active_orders"] > 0


def test_drawdown_threshold_permanently_pauses_trading():
    from src.backtesting.paper_trader import run_paper_trading_simulation

    initial_levels = tuple(
        Decimal(str(price))
        for price in range(60, 141, 8)
    )

    fake_candles = [
        {
            "timestamp": __import__("datetime").datetime(
                2026, 1, 1, hour,
                tzinfo=__import__("datetime").timezone.utc
            ),
            "open": price,
            "high": price + 0.5,
            "low": price - 0.5,
            "close": price,
            "volume": 1.0,
        }
        for hour, price in enumerate([100.0, 100.0, 70.0, 100.0])
    ]

    fake_config = {
        "starting_quote_balance": 1000.0,
        "drawdown_pause_fraction": 0.10,
        "atr_period": 14,
        "grid_intervals": 10,
        "boundary_atr_multiplier": 0.5,
        "minimum_range_atr": 6.0,
        "maximum_range_atr": 20.0,
    }

    manager = VirtualBalanceManager(
        available_quote=Decimal("500"),
        available_base=Decimal("5"),
    )

    old_orders = []

    for i, price in enumerate(range(91, 96), start=1):
        old_orders.append({
            "order_id": f"BUY-G001-{i}",
            "side": "buy",
            "price": Decimal(str(price)),
            "quantity": Decimal("1"),
            "status": "open",
        })

    for i, price in enumerate(range(106, 111), start=1):
        old_orders.append({
            "order_id": f"SELL-G001-{i}",
            "side": "sell",
            "price": Decimal(str(price)),
            "quantity": Decimal("0.001"),
            "status": "open",
        })

    for order in old_orders:
        manager.reserve_order(order)

    fake_state = {
        "config": fake_config,
        "candles": fake_candles,
        "lookback": 2,
        "initial_price": Decimal("100"),
        "initial_timestamp": fake_candles[1]["timestamp"].isoformat(),
        "starting_equity": Decimal("1000"),
        "initial_equity": Decimal("1000"),
        "balance_manager": manager,
        "active_grid": {"levels": list(initial_levels)},
        "active_grid_id": "G001",
        "active_grid_levels": initial_levels,
        "active_orders": old_orders,
        "all_orders": list(old_orders),
        "next_grid_number": 2,
    }

    valid_grid = {
        "levels": [float(level) for level in initial_levels],
    }

    with (
        patch(
            "src.backtesting.paper_trader.initialize_paper_trader",
            return_value=fake_state,
        ),
        patch(
            "src.backtesting.paper_trader.build_adaptive_grid",
            return_value=valid_grid,
        ),
        patch(
            "src.backtesting.paper_trader.execute_candle_orders",
            return_value=[],
        ),
    ):
        result = run_paper_trading_simulation()

    # The price drop must trigger the permanent pause.
    assert result["drawdown_paused"] is True

    # The original orders must all be cancelled.
    assert all(
        order["status"] == "cancelled"
        for order in old_orders
    )

    # All reservations must be released.
    assert manager.reserved_quote == Decimal("0")
    assert manager.reserved_base == Decimal("0")
    assert not manager._reservations

    # No replacement orders may be created.
    assert len(result["all_orders"]) == len(old_orders)

    # The bot must remain paused after the market recovers.
    assert all(
        entry["drawdown_paused"] is True
        for entry in result["equity_history"]
    )

    assert all(
        entry["grid_active"] is False
        for entry in result["equity_history"]
    )

    assert all(
        entry["active_orders"] == 0
        for entry in result["equity_history"]
    )


def test_new_orders_cannot_fill_on_the_candle_that_created_them():
    """Orders created after a candle closes cannot fill using that candle."""

    from src.backtesting.paper_trader import run_paper_trading_simulation

    candles = [
        {
            "timestamp": datetime(2026, 1, 1, i),
            "open": 100,
            "high": 100,
            "low": 100,
            "close": 100,
            "volume": 1,
        }
        for i in range(3)
    ]

    candles.append({
        "timestamp": datetime(2026, 1, 1, 3),
        "open": 100,
        "high": 120,
        "low": 80,
        "close": 100,
        "volume": 1,
    })

    config = {
        "lookback_candles": 3,
        "atr_period": 14,
        "grid_intervals": 10,
        "boundary_atr_multiplier": 0.5,
        "minimum_range_atr": 6.0,
        "maximum_range_atr": 20.0,
        "drawdown_pause_fraction": 0.10,
    }

    initial_levels = tuple(
        Decimal(str(price))
        for price in range(80, 121, 4)
    )

    fake_manager = VirtualBalanceManager(
        available_quote=Decimal("500"),
        available_base=Decimal("5"),
    )

    fake_state = {
        "config": config,
        "candles": candles,
        "lookback": 3,
        "balance_manager": fake_manager,
        "starting_equity": Decimal("1000"),
        "initial_equity": Decimal("1000"),
        "active_grid_id": "G001",
        "active_grid_levels": tuple(
            Decimal(str(price))
            for price in range(81, 122, 4)
        ),
        "active_orders": [],
        "all_orders": [],
        "next_grid_number": 2,
    }

    with patch(
        "src.backtesting.paper_trader.initialize_paper_trader",
        return_value=fake_state,
    ), patch(
        "src.backtesting.paper_trader.build_adaptive_grid",
        return_value={"levels": initial_levels},
    ):
        result = run_paper_trading_simulation()

    newly_created_orders = result["all_orders"]

    assert newly_created_orders
    assert all(
        order["status"] == "open"
        for order in newly_created_orders
    )
    assert result["trade_history"] == []
