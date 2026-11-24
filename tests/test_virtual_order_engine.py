
from decimal import Decimal
import pytest
from src.execution.virtual_order_engine import ( create_grid_orders, create_and_reserve_grid_orders )


def test_create_grid_orders_allocates_balances_equally():
    levels = [
        Decimal("60000"),
        Decimal("62000"),
        Decimal("64000"),
        Decimal("66000"),
        Decimal("68000"),
    ]

    market_price = Decimal("64000")

    orders = create_grid_orders(
        levels=levels,
        market_price=market_price,
        available_quote=Decimal("500"),
        available_base=Decimal("0.01"),
        timestamp="2026-11-16T12:00:00+00:00",
    )

    buy_orders = [order for order in orders if order["side"] == "buy"]
    sell_orders = [order for order in orders if order["side"] == "sell"]

    assert len(buy_orders) == 2
    assert len(sell_orders) == 2

    # Each buy order receives an equal USDT allocation.
    for order in buy_orders:
        order_value = order["quantity"] * order["price"]
        assert order_value <= Decimal("250")
        assert Decimal("250") - order_value < (
            order["price"] * Decimal("0.00000001")
        )

    # Each sell order receives an equal BTC allocation.
    for order in sell_orders:
        assert order["quantity"] == Decimal("0.005")

    assert all(order["status"] == "open" for order in orders)
    
    

def test_buy_orders_do_not_exceed_available_quote():
    levels = [
        Decimal("60000"),
        Decimal("62000"),
        Decimal("66000"),
        Decimal("68000"),
    ]

    orders = create_grid_orders(
        levels=levels,
        market_price=Decimal("64000"),
        available_quote=Decimal("500"),
        available_base=Decimal("0.01"),
        timestamp="2026-11-16T12:00:00+00:00",
    )

    buy_orders = [order for order in orders if order["side"] == "buy"]

    total_reserved_quote = sum(
        order["quantity"] * order["price"]
        for order in buy_orders
    )

    assert total_reserved_quote <= Decimal("500")


def test_create_and_reserve_grid_orders_updates_balances():
    from src.execution.balance_manager import VirtualBalanceManager

    manager = VirtualBalanceManager(
        available_quote=Decimal("500"),
        available_base=Decimal("0.01"),
    )

    orders = create_and_reserve_grid_orders(
        levels=[
            Decimal("60000"),
            Decimal("62000"),
            Decimal("64000"),
            Decimal("66000"),
            Decimal("68000"),
        ],
        market_price=Decimal("64000"),
        balance_manager=manager,
        timestamp="2026-11-16T12:00:00+00:00",
    )

    assert len(orders) == 4

    assert manager.available_quote < Decimal("500")
    assert manager.reserved_quote > Decimal("0")

    assert manager.available_base < Decimal("0.01")
    assert manager.reserved_base > Decimal("0")

    assert manager.available_quote + manager.reserved_quote == Decimal("500")
    assert manager.available_base + manager.reserved_base == Decimal("0.01")

def test_create_and_reserve_grid_orders_reserves_every_order():
    from src.execution.balance_manager import VirtualBalanceManager

    manager = VirtualBalanceManager(
        available_quote=Decimal("500"),
        available_base=Decimal("0.01"),
    )

    orders = create_and_reserve_grid_orders(
        levels=[
            Decimal("60000"),
            Decimal("62000"),
            Decimal("64000"),
            Decimal("66000"),
            Decimal("68000"),
        ],
        market_price=Decimal("64000"),
        balance_manager=manager,
        timestamp="2026-11-16T12:00:00+00:00",
    )

    for order in orders:
        assert order["order_id"] in manager._reservations


def test_failed_reservation_releases_previously_reserved_orders():
    from src.execution.balance_manager import VirtualBalanceManager

    manager = VirtualBalanceManager(
        available_quote=Decimal("500"),
        available_base=Decimal("0.01"),
    )

    original_reserve = manager.reserve_order

    def simulate_reservation_failure(order):
        if order["side"] == "sell":
            raise ValueError("Simulated reservation failure")

        return original_reserve(order)

    manager.reserve_order = simulate_reservation_failure

    with pytest.raises(ValueError, match="Simulated reservation failure"):
        create_and_reserve_grid_orders(
            levels=[
                Decimal("60000"),
                Decimal("62000"),
                Decimal("64000"),
                Decimal("66000"),
                Decimal("68000"),
            ],
            market_price=Decimal("64000"),
            balance_manager=manager,
            timestamp="2026-11-16T12:00:00+00:00",
        )

    # Previously reserved buy orders must be released.
    assert manager.available_quote == Decimal("500")
    assert manager.reserved_quote == Decimal("0")

    # No sell orders were successfully reserved.
    assert manager.available_base == Decimal("0.01")
    assert manager.reserved_base == Decimal("0")
