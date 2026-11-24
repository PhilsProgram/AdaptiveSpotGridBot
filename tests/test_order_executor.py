
from decimal import Decimal

from src.execution.order_executor import (
    find_executable_orders,
    execute_candle_orders,
)
from src.execution.balance_manager import VirtualBalanceManager


def test_finds_all_eligible_buy_and_sell_orders():
    orders = [
        {
            "order_id": "BUY-1",
            "side": "buy",
            "price": Decimal("80000"),
            "status": "open",
        },
        {
            "order_id": "BUY-2",
            "side": "buy",
            "price": Decimal("79000"),
            "status": "open",
        },
        {
            "order_id": "SELL-1",
            "side": "sell",
            "price": Decimal("82000"),
            "status": "open",
        },
    ]

    candle = {
        "open": Decimal("81000"),
        "high": Decimal("82500"),
        "low": Decimal("78500"),
        "close": Decimal("80500"),
    }

    executable = find_executable_orders(orders, candle)

    assert len(executable) == 3
    assert {order["order_id"] for order in executable} == {
        "BUY-1",
        "BUY-2",
        "SELL-1",
    }


def test_ignores_orders_whose_prices_were_not_reached():
    orders = [
        {
            "order_id": "BUY-1",
            "side": "buy",
            "price": Decimal("79000"),
            "status": "open",
        },
        {
            "order_id": "SELL-1",
            "side": "sell",
            "price": Decimal("83000"),
            "status": "open",
        },
    ]

    candle = {
        "open": Decimal("81000"),
        "high": Decimal("82500"),
        "low": Decimal("80000"),
        "close": Decimal("81500"),
    }

    executable = find_executable_orders(orders, candle)

    assert executable == []


def test_ignores_already_filled_orders():
    orders = [
        {
            "order_id": "BUY-1",
            "side": "buy",
            "price": Decimal("80000"),
            "status": "filled",
        },
    ]

    candle = {
        "open": Decimal("81000"),
        "high": Decimal("82000"),
        "low": Decimal("79000"),
        "close": Decimal("81500"),
    }

    executable = find_executable_orders(orders, candle)

    assert executable == []


def test_ignores_cancelled_orders():
    orders = [
        {
            "order_id": "SELL-1",
            "side": "sell",
            "price": Decimal("82000"),
            "status": "cancelled",
        },
    ]

    candle = {
        "open": Decimal("81000"),
        "high": Decimal("83000"),
        "low": Decimal("80000"),
        "close": Decimal("81500"),
    }

    executable = find_executable_orders(orders, candle)

    assert executable == []


def test_order_fills_when_candle_touches_exact_limit_price():
    orders = [
        {
            "order_id": "BUY-1",
            "side": "buy",
            "price": Decimal("80000"),
            "status": "open",
        },
        {
            "order_id": "SELL-1",
            "side": "sell",
            "price": Decimal("82000"),
            "status": "open",
        },
    ]

    candle = {
        "open": Decimal("81000"),
        "high": Decimal("82000"),
        "low": Decimal("80000"),
        "close": Decimal("81000"),
    }

    executable = find_executable_orders(orders, candle)

    assert len(executable) == 2
def test_order_detection_does_not_modify_order_status():
    orders = [
        {
            "order_id": "BUY-1",
            "side": "buy",
            "price": Decimal("80000"),
            "status": "open",
        },
    ]

    candle = {
        "high": Decimal("81000"),
        "low": Decimal("79000"),
    }

    executable = find_executable_orders(orders, candle)

    assert len(executable) == 1
    assert orders[0]["status"] == "open"
    

def test_execute_candle_orders_fills_eligible_orders_and_updates_balances():
    manager = VirtualBalanceManager(
        available_quote=Decimal("1000"),
        available_base=Decimal("1"),
    )

    orders = [
        {
            "order_id": "BUY-1",
            "side": "buy",
            "price": Decimal("100"),
            "quantity": Decimal("2"),
            "status": "open",
            "filled_at": None,
        },
        {
            "order_id": "SELL-1",
            "side": "sell",
            "price": Decimal("120"),
            "quantity": Decimal("0.5"),
            "status": "open",
            "filled_at": None,
        },
    ]

    for order in orders:
        manager.reserve_order(order)

    candle = {
        "high": Decimal("125"),
        "low": Decimal("95"),
        "timestamp": "2026-11-18T15:00:00Z",
    }

    filled = execute_candle_orders(
        orders,
        candle,
        manager,
    )

    assert len(filled) == 2
    assert all(order["status"] == "filled" for order in orders)

    assert all(
        order["filled_at"] == candle["timestamp"]
        for order in orders
    )

    assert manager.available_quote == Decimal("860")
    assert manager.available_base == Decimal("2.5")
    assert manager.reserved_quote == Decimal("0")
    assert manager.reserved_base == Decimal("0")


def test_execute_candle_orders_leaves_unreached_orders_open():
    manager = VirtualBalanceManager(
        available_quote=Decimal("1000"),
        available_base=Decimal("1"),
    )

    order = {
        "order_id": "BUY-1",
        "side": "buy",
        "price": Decimal("90"),
        "quantity": Decimal("2"),
        "status": "open",
        "filled_at": None,
    }

    manager.reserve_order(order)

    candle = {
        "high": Decimal("110"),
        "low": Decimal("100"),
        "timestamp": "2026-11-18T15:00:00Z",
    }

    filled = execute_candle_orders(
        [order],
        candle,
        manager,
    )

    assert filled == []
    assert order["status"] == "open"
    assert order["filled_at"] is None

    assert manager.reserved_quote == Decimal("180")
    assert manager.available_quote == Decimal("820")
