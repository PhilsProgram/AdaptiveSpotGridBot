
from decimal import Decimal


def find_executable_orders(
    orders: list[dict],
    candle: dict,
) -> list[dict]:
    """Find open orders reached by a completed candle."""

    candle_high = Decimal(str(candle["high"]))
    candle_low = Decimal(str(candle["low"]))

    if not candle_low.is_finite() or not candle_high.is_finite():
        raise ValueError("Candle prices must be finite")

    if candle_low <= 0 or candle_high <= 0:
        raise ValueError("Candle prices must be positive")

    if candle_low > candle_high:
        raise ValueError("Candle low cannot exceed candle high")

    executable_orders = []

    for order in orders:
        if order["status"] != "open":
            continue

        order_price = Decimal(str(order["price"]))

        if not order_price.is_finite() or order_price <= 0:
            raise ValueError("Order price must be positive and finite")

        if order["side"] == "buy":
            if candle_low <= order_price:
                executable_orders.append(order)

        elif order["side"] == "sell":
            if candle_high >= order_price:
                executable_orders.append(order)

        else:
            raise ValueError(f"Invalid order side: {order['side']}")

    return executable_orders



def execute_candle_orders(
    orders: list[dict],
    candle: dict,
    balance_manager,
) -> list[dict]:
    """Execute eligible orders using a completed candle."""

    # Only orders that existed before this candle are considered.
    existing_orders = list(orders)

    executable_orders = find_executable_orders(
        existing_orders,
        candle,
    )

    filled_orders = []

    for order in executable_orders:
        balance_manager.fill_order(order)

        order["filled_at"] = candle["timestamp"]

        filled_orders.append(order)

    return filled_orders
