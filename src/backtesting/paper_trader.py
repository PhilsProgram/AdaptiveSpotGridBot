
from decimal import Decimal, ROUND_DOWN

from src.config_loader import load_config
from src.market_data.historical_data import prepare_historical_data
from src.strategy.grid_builder import (
    build_adaptive_grid,
    GridRejectedError,
)
from src.execution.balance_manager import VirtualBalanceManager
from src.execution.virtual_order_engine import create_and_reserve_grid_orders
from src.execution.order_executor import execute_candle_orders



BTC_PRECISION = Decimal("0.00000001")


def initialize_paper_trader(
    csv_path: str = "data/btc_usdt_1h_90d.csv",
    config_path: str | None = None,
) -> dict:
    """Initialize the paper trader and create its first virtual grid."""

    # 1. Load strategy configuration.
    config = load_config(config_path)

    lookback = config["lookback_candles"]
    atr_period = config["atr_period"]

    # 2. Load completed historical candles.
    candles = prepare_historical_data(
        csv_path,
        minimum_candles=lookback,
    )

    if len(candles) < lookback:
        raise ValueError(
            f"At least {lookback} completed candles are required"
        )

    # 3. Use the first lookback candles to establish the initial grid.
    initial_candles = candles[:lookback]

    highs = [candle["high"] for candle in initial_candles]
    lows = [candle["low"] for candle in initial_candles]
    closes = [candle["close"] for candle in initial_candles]

    initial_price = Decimal(str(initial_candles[-1]["close"]))

    grid = build_adaptive_grid(
        highs=highs,
        lows=lows,
        closes=closes,
        atr_period=atr_period,
        lookback=lookback,
        intervals=config["grid_intervals"],
        boundary_atr_multiplier=config["boundary_atr_multiplier"],
        minimum_range_atr=config["minimum_range_atr"],
        maximum_range_atr=config["maximum_range_atr"],
    )

    # 4. Establish the initial virtual portfolio.
    starting_balance = Decimal(str(config["starting_quote_balance"]))

    quote_allocation = Decimal(
        str(config["initial_quote_allocation"])
    )

    base_allocation = Decimal(
        str(config["initial_base_allocation"])
    )

    initial_quote = starting_balance * quote_allocation

    initial_base = (
        starting_balance * base_allocation / initial_price
    ).quantize(BTC_PRECISION, rounding=ROUND_DOWN)

    balance_manager = VirtualBalanceManager(
        available_quote=initial_quote,
        available_base=initial_base,
    )

    # 5. Create and reserve the first grid's virtual orders.
    initial_timestamp = initial_candles[-1]["timestamp"].isoformat()

    grid_id = "G001"

    initial_orders = create_and_reserve_grid_orders(
        levels=[Decimal(str(level)) for level in grid["levels"]],
        market_price=initial_price,
        balance_manager=balance_manager,
        timestamp=initial_timestamp,
        grid_id=grid_id,
    )

    # 6. Record the initial portfolio value.
    initial_equity = (
        balance_manager.available_quote
        + balance_manager.reserved_quote
        + (
            balance_manager.available_base
            + balance_manager.reserved_base
        ) * initial_price
    )

    return {
        "config": config,
        "candles": candles,
        "lookback": lookback,
        "initial_price": initial_price,
        "initial_timestamp": initial_timestamp,
        "starting_equity": starting_balance,
        "initial_equity": initial_equity,
        "balance_manager": balance_manager,
        "active_grid": grid,
        "active_grid_id": grid_id,
        "active_grid_levels": tuple(
            Decimal(str(level)) for level in grid["levels"]
        ),
        "active_orders": list(initial_orders),
        "all_orders": list(initial_orders),
        "next_grid_number": 2,
    }


def cancel_open_orders(
    orders: list[dict],
    balance_manager: VirtualBalanceManager,
) -> int:
    """Cancel open orders and release their reserved balances."""

    cancelled_count = 0

    for order in orders:
        if order["status"] != "open":
            continue

        balance_manager.release_order(order["order_id"])
        order["status"] = "cancelled"
        cancelled_count += 1

    return cancelled_count


def calculate_portfolio_equity(
    balance_manager: VirtualBalanceManager,
    market_price: Decimal,
) -> Decimal:
    """Calculate total portfolio value, including reserved assets."""

    market_price = Decimal(str(market_price))

    total_quote = (
        balance_manager.available_quote
        + balance_manager.reserved_quote
    )

    total_base = (
        balance_manager.available_base
        + balance_manager.reserved_base
    )

    return total_quote + (total_base * market_price)



def run_paper_trading_simulation(
    csv_path: str = "data/btc_usdt_1h_90d.csv",
    config_path: str | None = None,
) -> dict:
    """Run the complete historical paper-trading simulation."""

    state = initialize_paper_trader(
        csv_path=csv_path,
        config_path=config_path,
    )

    config = state["config"]
    candles = state["candles"]
    lookback = state["lookback"]
    balance_manager = state["balance_manager"]

    active_orders = state["active_orders"]
    all_orders = state["all_orders"]

    active_grid_levels = state["active_grid_levels"]
    grid_id = state["active_grid_id"]
    next_grid_number = state["next_grid_number"]

    equity_history = []
    trade_history = []
    grid_history = []
    rejected_grids = []

    peak_equity = state["initial_equity"]
    drawdown_paused = False

    for index in range(lookback, len(candles)):

        candle = candles[index]

        candle_timestamp = candle["timestamp"].isoformat()
        market_price = Decimal(str(candle["close"]))

        # 1. Execute only orders that existed before this candle.
        filled_orders = execute_candle_orders(
            orders=active_orders,
            candle=candle,
            balance_manager=balance_manager,
        )

        trade_history.extend(filled_orders)

        # 2. Calculate equity after processing the candle's fills.
        equity = calculate_portfolio_equity(
            balance_manager,
            market_price,
        )

        peak_equity = max(peak_equity, equity)

        drawdown = max(
            Decimal("0"),
            (
                state["starting_equity"] - equity
            ) / state["starting_equity"],
        )

        # 3. Activate a permanent trading pause when the threshold is reached.
        if (
            drawdown >= Decimal(str(config["drawdown_pause_fraction"]))
            and not drawdown_paused
        ):
            drawdown_paused = True

            cancel_open_orders(
                active_orders,
                balance_manager,
            )

            active_orders = []
            active_grid_levels = None
            grid_id = None

        # 4. Recalculate the grid using data available through this candle.
        history = candles[:index + 1]

        highs = [item["high"] for item in history]
        lows = [item["low"] for item in history]
        closes = [item["close"] for item in history]

        try:
            new_grid = build_adaptive_grid(
                highs=highs,
                lows=lows,
                closes=closes,
                atr_period=config["atr_period"],
                lookback=lookback,
                intervals=config["grid_intervals"],
                boundary_atr_multiplier=config["boundary_atr_multiplier"],
                minimum_range_atr=config["minimum_range_atr"],
                maximum_range_atr=config["maximum_range_atr"],
            )

        except GridRejectedError as error:

            cancelled_count = cancel_open_orders(
                active_orders,
                balance_manager,
            )

            active_orders = []
            active_grid_levels = None
            grid_id = None

            rejected_grids.append({
                "timestamp": candle_timestamp,
                "reason": str(error),
                "cancelled_orders": cancelled_count,
            })

        else:
            new_levels = tuple(
                Decimal(str(level))
                for level in new_grid["levels"]
            )

            # 5. Only manage orders if trading has not been paused.
            if not drawdown_paused:

                # Keep existing orders if every grid level is unchanged.
                if new_levels != active_grid_levels:

                    cancel_open_orders(
                        active_orders,
                        balance_manager,
                    )

                    active_orders = []

                    new_grid_id = f"G{next_grid_number:03d}"

                    new_orders = create_and_reserve_grid_orders(
                        levels=list(new_levels),
                        market_price=market_price,
                        balance_manager=balance_manager,
                        timestamp=candle_timestamp,
                        grid_id=new_grid_id,
                    )

                    active_orders = new_orders
                    all_orders.extend(new_orders)

                    active_grid_levels = new_levels
                    grid_id = new_grid_id
                    next_grid_number += 1

            else:
                # Continue calculating grids, but never resume trading.
                active_orders = []
                active_grid_levels = None
                grid_id = None

            grid_history.append({
                "timestamp": candle_timestamp,
                "grid_id": grid_id,
                "levels": new_levels,
                "trading_paused": drawdown_paused,
            })

        # 6. Record portfolio value after all processing.
        equity = calculate_portfolio_equity(
            balance_manager,
            market_price,
        )

        equity_history.append({
            "timestamp": candle_timestamp,
            "market_price": market_price,
            "equity": equity,
            "peak_equity": peak_equity,
            "drawdown": drawdown,
            "active_orders": sum(
                1 for order in active_orders
                if order["status"] == "open"
            ),
            "drawdown_paused": drawdown_paused,
            "grid_active": (
                active_grid_levels is not None
                and not drawdown_paused
            ),
        })

    return {
        "config": config,
        "starting_equity": state["starting_equity"],
        "initial_equity": state["initial_equity"],
        "final_equity": (
            equity_history[-1]["equity"]
            if equity_history
            else state["initial_equity"]
        ),
        "final_balances": {
            "available_quote": balance_manager.available_quote,
            "reserved_quote": balance_manager.reserved_quote,
            "available_base": balance_manager.available_base,
            "reserved_base": balance_manager.reserved_base,
        },
        "all_orders": all_orders,
        "trade_history": trade_history,
        "equity_history": equity_history,
        "grid_history": grid_history,
        "rejected_grids": rejected_grids,
        "drawdown_paused": drawdown_paused,
        "peak_equity": peak_equity,
    }
