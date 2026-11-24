
from decimal import Decimal

import pytest

from src.execution.balance_manager import VirtualBalanceManager


def test_initial_balances_are_available_and_nothing_is_reserved():
    manager = VirtualBalanceManager(
        available_quote=Decimal("500"),
        available_base=Decimal("0.01"),
    )

    assert manager.available_quote == Decimal("500")
    assert manager.available_base == Decimal("0.01")
    assert manager.reserved_quote == Decimal("0")
    assert manager.reserved_base == Decimal("0")


def test_reserving_buy_order_moves_usdt_to_reserved_balance():
    manager = VirtualBalanceManager(
        available_quote=Decimal("500"),
        available_base=Decimal("0.01"),
    )

    order = {
        "order_id": "BUY-1",
        "side": "buy",
        "price": Decimal("60000"),
        "quantity": Decimal("0.004"),
    }

    reserved = manager.reserve_order(order)

    assert reserved == Decimal("240.000")
    assert manager.available_quote == Decimal("260.000")
    assert manager.reserved_quote == Decimal("240.000")


def test_reserving_sell_order_moves_btc_to_reserved_balance():
    manager = VirtualBalanceManager(
        available_quote=Decimal("500"),
        available_base=Decimal("0.01"),
    )

    order = {
        "order_id": "SELL-1",
        "side": "sell",
        "price": Decimal("68000"),
        "quantity": Decimal("0.004"),
    }

    reserved = manager.reserve_order(order)

    assert reserved == Decimal("0.004")
    assert manager.available_base == Decimal("0.006")
    assert manager.reserved_base == Decimal("0.004")


def test_cancelling_buy_order_releases_reserved_usdt():
    manager = VirtualBalanceManager(
        available_quote=Decimal("500"),
        available_base=Decimal("0.01"),
    )

    order = {
        "order_id": "BUY-1",
        "side": "buy",
        "price": Decimal("60000"),
        "quantity": Decimal("0.004"),
    }

    manager.reserve_order(order)
    manager.release_order("BUY-1")

    assert manager.available_quote == Decimal("500")
    assert manager.reserved_quote == Decimal("0")


def test_cancelling_sell_order_releases_reserved_btc():
    manager = VirtualBalanceManager(
        available_quote=Decimal("500"),
        available_base=Decimal("0.01"),
    )

    order = {
        "order_id": "SELL-1",
        "side": "sell",
        "price": Decimal("68000"),
        "quantity": Decimal("0.004"),
    }

    manager.reserve_order(order)
    manager.release_order("SELL-1")

    assert manager.available_base == Decimal("0.01")
    assert manager.reserved_base == Decimal("0")


def test_cannot_reserve_more_usdt_than_available():
    manager = VirtualBalanceManager(
        available_quote=Decimal("100"),
        available_base=Decimal("0.01"),
    )

    order = {
        "order_id": "BUY-1",
        "side": "buy",
        "price": Decimal("60000"),
        "quantity": Decimal("0.002"),
    }

    with pytest.raises(ValueError, match="Insufficient available quote"):
        manager.reserve_order(order)


def test_cannot_reserve_more_btc_than_available():
    manager = VirtualBalanceManager(
        available_quote=Decimal("500"),
        available_base=Decimal("0.001"),
    )

    order = {
        "order_id": "SELL-1",
        "side": "sell",
        "price": Decimal("68000"),
        "quantity": Decimal("0.002"),
    }

    with pytest.raises(ValueError, match="Insufficient available base"):
        manager.reserve_order(order)


def test_cannot_reserve_the_same_order_twice():
    manager = VirtualBalanceManager(
        available_quote=Decimal("500"),
        available_base=Decimal("0.01"),
    )

    order = {
        "order_id": "BUY-1",
        "side": "buy",
        "price": Decimal("60000"),
        "quantity": Decimal("0.004"),
    }

    manager.reserve_order(order)

    with pytest.raises(ValueError, match="already reserved"):
        manager.reserve_order(order)

    # The first reservation must remain unchanged.
    assert manager.available_quote == Decimal("260.000")
    assert manager.reserved_quote == Decimal("240.000")

def test_fill_buy_order_updates_balances():
    manager = VirtualBalanceManager(
        available_quote=Decimal("500"),
        available_base=Decimal("1"),
    )

    order = {
        "order_id": "BUY-1",
        "side": "buy",
        "price": Decimal("50000"),
        "quantity": Decimal("0.01"),
        "status": "open",
    }

    manager.reserve_order(order)
    result = manager.fill_order(order)

    assert result == Decimal("500")
    assert manager.available_quote == Decimal("0")
    assert manager.reserved_quote == Decimal("0")
    assert manager.available_base == Decimal("1.01")
    assert manager.reserved_base == Decimal("0")
    assert order["status"] == "filled"


def test_fill_sell_order_updates_balances():
    manager = VirtualBalanceManager(
        available_quote=Decimal("500"),
        available_base=Decimal("1"),
    )

    order = {
        "order_id": "SELL-1",
        "side": "sell",
        "price": Decimal("50000"),
        "quantity": Decimal("0.01"),
        "status": "open",
    }

    manager.reserve_order(order)
    result = manager.fill_order(order)

    assert result == Decimal("500")
    assert manager.available_quote == Decimal("1000")
    assert manager.reserved_quote == Decimal("0")
    assert manager.available_base == Decimal("0.99")
    assert manager.reserved_base == Decimal("0")
    assert order["status"] == "filled"
    
    

def test_cannot_fill_an_order_twice():
    manager = VirtualBalanceManager(
        available_quote=Decimal("1000"),
        available_base=Decimal("0"),
    )

    order = {
        "order_id": "BUY-1",
        "side": "buy",
        "price": Decimal("100"),
        "quantity": Decimal("2"),
        "status": "open",
    }

    manager.reserve_order(order)
    manager.fill_order(order)

    with pytest.raises(ValueError, match="No reservation found"):
        manager.fill_order(order)


def test_cannot_fill_order_without_reservation():
    manager = VirtualBalanceManager(
        available_quote=Decimal("1000"),
        available_base=Decimal("0"),
    )

    order = {
        "order_id": "BUY-2",
        "side": "buy",
        "price": Decimal("100"),
        "quantity": Decimal("2"),
        "status": "open",
    }

    with pytest.raises(ValueError, match="No reservation found"):
        manager.fill_order(order)


def test_cannot_fill_cancelled_order():
    manager = VirtualBalanceManager(
        available_quote=Decimal("1000"),
        available_base=Decimal("0"),
    )

    order = {
        "order_id": "BUY-3",
        "side": "buy",
        "price": Decimal("100"),
        "quantity": Decimal("2"),
        "status": "cancelled",
    }

    manager.reserve_order(order)

    with pytest.raises(ValueError, match="Only open orders can be filled"):
        manager.fill_order(order)
