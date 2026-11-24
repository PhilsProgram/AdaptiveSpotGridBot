
from decimal import Decimal, ROUND_DOWN
from src.execution.balance_manager import VirtualBalanceManager

BTC_PRECISION = Decimal("0.00000001")


def create_grid_orders(
    levels: list[Decimal],
    market_price: Decimal,
    available_quote: Decimal,
    available_base: Decimal,
    timestamp: str,
    grid_id: str | None = None,
) -> list[dict]:
    """Create equally funded virtual buy and sell orders."""

    levels = [Decimal(str(level)) for level in levels]
    market_price = Decimal(str(market_price))
    available_quote = Decimal(str(available_quote))
    available_base = Decimal(str(available_base))

    if market_price <= 0:
        raise ValueError("Market price must be positive")

    if available_quote < 0 or available_base < 0:
        raise ValueError("Available balances cannot be negative")

    if any(level <= 0 for level in levels):
        raise ValueError("Grid levels must be positive")

    if len(set(levels)) != len(levels):
        raise ValueError("Grid levels must be unique")

    buy_levels = sorted(
        (level for level in levels if level < market_price),
        reverse=True,
    )

    sell_levels = sorted(
        level for level in levels if level > market_price
    )

    orders = []

    buy_id_prefix = f"BUY-{grid_id}-" if grid_id else "BUY-"
    sell_id_prefix = f"SELL-{grid_id}-" if grid_id else "SELL-"

    # Divide available USDT equally among buy orders.
    if buy_levels:
        quote_per_order = available_quote / len(buy_levels)

        for index, price in enumerate(buy_levels, start=1):
            quantity = (
                quote_per_order / price
            ).quantize(BTC_PRECISION, rounding=ROUND_DOWN)

            if quantity <= 0:
                continue

            orders.append({
                "order_id": f"{buy_id_prefix}{index}",
                "side": "buy",
                "price": price,
                "quantity": quantity,
                "status": "open",
                "created_at": timestamp,
                "filled_at": None,
            })

    # Divide available BTC equally among sell orders.
    if sell_levels:
        base_per_order = (
            available_base / len(sell_levels)
        ).quantize(BTC_PRECISION, rounding=ROUND_DOWN)

        for index, price in enumerate(sell_levels, start=1):
            if base_per_order <= 0:
                continue

            orders.append({
                "order_id": f"{sell_id_prefix}{index}",
                "side": "sell",
                "price": price,
                "quantity": base_per_order,
                "status": "open",
                "created_at": timestamp,
                "filled_at": None,
            })

    return orders


def create_and_reserve_grid_orders(
    levels: list[Decimal],
    market_price: Decimal,
    balance_manager: VirtualBalanceManager,
    timestamp: str,
    grid_id: str | None = None,
) -> list[dict]:
    """Create grid orders and reserve their required balances."""

    orders = create_grid_orders(
        levels=levels,
        market_price=market_price,
        available_quote=balance_manager.available_quote,
        available_base=balance_manager.available_base,
        timestamp=timestamp,
        grid_id=grid_id,
    )

    reserved_orders = []

    try:
        for order in orders:
            balance_manager.reserve_order(order)
            reserved_orders.append(order)

    except Exception:
        for order in reversed(reserved_orders):
            balance_manager.release_order(order["order_id"])

        raise

    return orders
