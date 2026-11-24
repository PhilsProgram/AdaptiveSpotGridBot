
from decimal import Decimal, InvalidOperation

class VirtualBalanceManager:
    """Tracks available and reserved virtual trading balances."""

    def __init__(
        self,
        available_quote: Decimal,
        available_base: Decimal,
    ):
        self.available_quote = self._to_decimal(
            available_quote, "available_quote"
        )
        self.available_base = self._to_decimal(
            available_base, "available_base"
        )

        if self.available_quote < 0 or self.available_base < 0:
            raise ValueError("Initial balances cannot be negative")

        self.reserved_quote = Decimal("0")
        self.reserved_base = Decimal("0")

        # Records the funds reserved for each open order.
        self._reservations = {}

    @staticmethod
    def _to_decimal(value, field_name):
        try:
            result = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError(f"{field_name} must be a valid number")

        if not result.is_finite():
            raise ValueError(f"{field_name} must be finite")

        return result

    def reserve_order(self, order: dict) -> Decimal:
        """Move funds from available balances to reserved balances."""

        order_id = order.get("order_id")
        side = order.get("side")

        if not order_id:
            raise ValueError("Order must have an order_id")

        if order_id in self._reservations:
            raise ValueError(f"Order {order_id} is already reserved")

        if side not in ("buy", "sell"):
            raise ValueError("Order side must be buy or sell")

        quantity = self._to_decimal(
            order.get("quantity"), "quantity"
        )
        price = self._to_decimal(
            order.get("price"), "price"
        )

        if quantity <= 0 or price <= 0:
            raise ValueError("Order quantity and price must be positive")

        if side == "buy":
            amount = quantity * price

            if amount > self.available_quote:
                raise ValueError("Insufficient available quote balance")

            self.available_quote -= amount
            self.reserved_quote += amount
            asset = "quote"

        else:
            amount = quantity

            if amount > self.available_base:
                raise ValueError("Insufficient available base balance")

            self.available_base -= amount
            self.reserved_base += amount
            asset = "base"

        self._reservations[order_id] = {
            "asset": asset,
            "amount": amount,
        }

        return amount

    def release_order(self, order_id: str) -> Decimal:
        """Return reserved funds when an order is cancelled."""

        if order_id not in self._reservations:
            raise ValueError(f"No reservation found for order {order_id}")

        reservation = self._reservations.pop(order_id)
        amount = reservation["amount"]

        if reservation["asset"] == "quote":
            self.reserved_quote -= amount
            self.available_quote += amount

        else:
            self.reserved_base -= amount
            self.available_base += amount

        return amount
    
    
    def fill_order(self, order: dict) -> Decimal:
        """Consume reserved funds and credit the asset received."""

        order_id = order.get("order_id")

        if not order_id or order_id not in self._reservations:
            raise ValueError(
                f"No reservation found for order {order_id}"
            )

        if order.get("status") != "open":
            raise ValueError("Only open orders can be filled")

        side = order.get("side")

        if side not in ("buy", "sell"):
            raise ValueError("Order side must be buy or sell")

        quantity = self._to_decimal(
            order.get("quantity"), "quantity"
        )

        price = self._to_decimal(
            order.get("price"), "price"
        )

        if quantity <= 0 or price <= 0:
            raise ValueError("Order quantity and price must be positive")

        reservation = self._reservations[order_id]
        amount = reservation["amount"]

        if side == "buy":
            expected_cost = quantity * price

            if reservation["asset"] != "quote" or amount != expected_cost:
                raise ValueError("Buy order reservation does not match order")

            self.reserved_quote -= amount
            self.available_base += quantity

        else:
            if reservation["asset"] != "base" or amount != quantity:
                raise ValueError("Sell order reservation does not match order")

            self.reserved_base -= amount
            self.available_quote += quantity * price

        del self._reservations[order_id]

        order["status"] = "filled"

        return quantity * price
