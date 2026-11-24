
from src.config_loader import load_config
from src.market_data.historical_data import prepare_historical_data
from src.strategy.grid_builder import (
    build_adaptive_grid,
    GridRejectedError,
)
from src.strategy.volatility import calculate_atr


def run_grid_behavior_simulation(
    candles: list[dict],
    config: dict,
) -> list[dict]:
    """Replay supplied completed candles and record adaptive grid behaviour."""

    atr_period = config["atr_period"]
    lookback = config["lookback_candles"]
    intervals = config["grid_intervals"]

    minimum_candles = max(atr_period, lookback)

    if len(candles) < minimum_candles:
        raise ValueError(
            f"Not enough candles. Required: {minimum_candles}, "
            f"available: {len(candles)}"
        )

    results = []

    for current_index in range(minimum_candles, len(candles) + 1):
        historical_window = candles[:current_index]

        highs = [candle["high"] for candle in historical_window]
        lows = [candle["low"] for candle in historical_window]
        closes = [candle["close"] for candle in historical_window]

        current_candle = candles[current_index - 1]

        try:
            grid = build_adaptive_grid(
                highs=highs,
                lows=lows,
                closes=closes,
                atr_period=atr_period,
                lookback=lookback,
                intervals=intervals,
                boundary_atr_multiplier=config["boundary_atr_multiplier"],
                minimum_range_atr=config["minimum_range_atr"],
                maximum_range_atr=config["maximum_range_atr"],
            )

        except GridRejectedError as exc:
            atr_value = calculate_atr(
                highs,
                lows,
                closes,
                period=atr_period,
            )

            recent_high = max(highs[-lookback:])
            recent_low = min(lows[-lookback:])

            raw_width = (
                recent_high
                - recent_low
                + 2 * config["boundary_atr_multiplier"] * atr_value
            )
            
            recent_range = recent_high - recent_low

            range_atr = recent_range / atr_value

            results.append({
                "timestamp": current_candle["timestamp"],
                "market_price": current_candle["close"],
                "atr": atr_value,
                "recent_high": recent_high,
                "recent_low": recent_low,
                "grid_width": raw_width,
                "grid_width_atr": raw_width / atr_value,
                "status": "rejected",
                "reason": str(exc),
                "levels": [],
                "range_atr": range_atr
            })

            continue

        lower_bound = grid["lower_bound"]
        upper_bound = grid["upper_bound"]

        percentage_spacing = (
            (upper_bound / lower_bound) ** (1 / intervals) - 1
        ) * 100
        
        recent_range = grid["recent_high"] - grid["recent_low"]
        range_atr = recent_range / grid["atr"]

        results.append({
            "timestamp": current_candle["timestamp"],
            "market_price": current_candle["close"],
            "atr": grid["atr"],
            "recent_high": grid["recent_high"],
            "recent_low": grid["recent_low"],
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "grid_width": upper_bound - lower_bound,
            "percentage_spacing": percentage_spacing,
            "grid_width_atr": (upper_bound - lower_bound) / grid["atr"],
            "status": "active",
            "levels": grid["levels"],
            "range_atr": range_atr,
        })

    return results


def simulate_grid_behavior(
    csv_path="data/btc_usdt_1h_90d.csv",
    config_path="config/strategy.json",
) -> list[dict]:
    """Load historical data and run the grid behaviour simulation."""

    config = load_config(config_path)

    minimum_candles = max(
        config["atr_period"],
        config["lookback_candles"],
    )

    candles = prepare_historical_data(
        csv_path,
        minimum_candles=minimum_candles,
    )

    return run_grid_behavior_simulation(candles, config)


if __name__ == "__main__":
    simulation_results = simulate_grid_behavior(
        config_path="config/strategy.json"
    )

    total = len(simulation_results)

    active_results = [
        result
        for result in simulation_results
        if result["status"] == "active"
    ]

    rejected_results = [
        result
        for result in simulation_results
        if result["status"] == "rejected"
    ]

    active_count = len(active_results)
    rejected_count = len(rejected_results)
    
        # Rejection analysis
    rejection_widths = [
        result["grid_width_atr"]
        for result in rejected_results
    ]

    average_rejected_width = (
        sum(rejection_widths) / len(rejection_widths)
        if rejection_widths else 0
    )

    maximum_rejected_width = (
        max(rejection_widths)
        if rejection_widths else 0
    )

    longest_rejection_streak = 0
    current_rejection_streak = 0
    rejection_streak_count = 0
    
    rejection_periods = []
    current_period = []

    recovery_delays = []
    calculations_since_rejection = None

    for result in simulation_results:
        if result["status"] == "rejected":
            if current_rejection_streak == 0:
                rejection_streak_count += 1

            current_rejection_streak += 1
            current_period.append(result)

            longest_rejection_streak = max(
                longest_rejection_streak,
                current_rejection_streak
            )

            calculations_since_rejection = 0

        else:
            if current_period:
                period_widths = [
                    item["grid_width_atr"]
                    for item in current_period
                ]
                
                period_range_atr = [
                    item["range_atr"]
                    for item in current_period
                ]

                rejection_periods.append({
                    "start": current_period[0]["timestamp"],
                    "end": current_period[-1]["timestamp"],
                    "candles": len(current_period),
                    "average_width": sum(period_widths) / len(period_widths),
                    "maximum_width": max(period_widths),
                    "average_range_atr": sum(period_range_atr) / len(period_range_atr),
                    "maximum_range_atr": max(period_range_atr),
                })

                current_period = []

            current_rejection_streak = 0

            if calculations_since_rejection is not None:
                calculations_since_rejection += 1
                recovery_delays.append(calculations_since_rejection)
                calculations_since_rejection = None

    # Include a rejection period that continues until the end of the dataset.
    if current_period:
        period_widths = [
            item["grid_width_atr"]
            for item in current_period
        ]

        rejection_periods.append({
            "start": current_period[0]["timestamp"],
            "end": current_period[-1]["timestamp"],
            "candles": len(current_period),
            "average_width": sum(period_widths) / len(period_widths),
            "maximum_width": max(period_widths),
        })

    average_recovery_delay = (
        sum(recovery_delays) / len(recovery_delays)
        if recovery_delays else 0
    )

    maximum_recovery_delay = (
        max(recovery_delays)
        if recovery_delays else 0
    )

    active_percentage = (
        active_count / total * 100 if total else 0
    )

    rejected_percentage = (
        rejected_count / total * 100 if total else 0
    )

    print("\nADAPTIVE GRID SIMULATION COMPLETE")
    print("---------------------------------")
    print(f"Total calculations: {total}")
    print(f"Accepted grids: {active_count}")
    print(f"Rejected grids: {rejected_count}")
    print(f"Active percentage: {active_percentage:.2f}%")
    print(f"Rejected percentage: {rejected_percentage:.2f}%")
    
    print("\nINDIVIDUAL REJECTION PERIODS")
    print("----------------------------")

    for index, period in enumerate(rejection_periods, start=1):
        print(
            f"Period {index}: "
            f"{period['start']} to {period['end']} | "
            f"Duration: {period['candles']} candles | "
            f"Average range: {period['average_range_atr']:.2f} ATR | "
            f"Maximum range: {period['maximum_range_atr']:.2f} ATR | "
            f"Average grid width: {period['average_width']:.2f} ATR | "
            f"Maximum grid width: {period['maximum_width']:.2f} ATR"
        )
    
    print("\nREJECTION ANALYSIS")
    print("------------------")
    print(f"Number of rejection periods: {rejection_streak_count}")
    print(f"Longest rejection streak: {longest_rejection_streak} candles")
    print(f"Average rejected grid width: {average_rejected_width:.2f} ATR")
    print(f"Maximum rejected grid width: {maximum_rejected_width:.2f} ATR")
    print(f"Completed recovery periods: {len(recovery_delays)}")
    print(f"Average recovery delay: {average_recovery_delay:.2f} candles")
    print(f"Maximum recovery delay: {maximum_recovery_delay} candles")

    if active_results:
        first = active_results[0]
        latest = active_results[-1]

        print("\nFIRST ACCEPTED GRID")
        print(f"Timestamp: {first['timestamp']}")
        print(f"Market price: {first['market_price']:.2f}")
        print(f"Lower boundary: {first['lower_bound']:.2f}")
        print(f"Upper boundary: {first['upper_bound']:.2f}")
        print(f"ATR: {first['atr']:.2f}")
        print(f"Grid width in ATR: {first['grid_width_atr']:.2f}")
        print(f"Percentage spacing: {first['percentage_spacing']:.4f}%")

        print("\nLATEST ACCEPTED GRID")
        print(f"Timestamp: {latest['timestamp']}")
        print(f"Market price: {latest['market_price']:.2f}")
        print(f"Lower boundary: {latest['lower_bound']:.2f}")
        print(f"Upper boundary: {latest['upper_bound']:.2f}")
        print(f"ATR: {latest['atr']:.2f}")
        print(f"Grid width in ATR: {latest['grid_width_atr']:.2f}")
        print(f"Percentage spacing: {latest['percentage_spacing']:.4f}%")

        print("\nLATEST GRID LEVELS")

        for index, level in enumerate(latest["levels"]):
            print(f"Level {index}: {level:.2f}")
            
        if rejected_results:
            print("\nALL REJECTION PERIODS")
            print("---------------------")

        rejection_groups = []
        current_group = []

        for result in simulation_results:
            if result["status"] == "rejected":
                current_group.append(result)
            else:
                if current_group:
                    rejection_groups.append(current_group)
                    current_group = []

        if current_group:
            rejection_groups.append(current_group)

        for index, group in enumerate(rejection_groups, start=1):
            start_time = group[0]["timestamp"]
            end_time = group[-1]["timestamp"]

            duration = len(group)

            maximum_width = max(
                item["grid_width_atr"]
                for item in group
            )

            average_width = sum(
                item["grid_width_atr"]
                for item in group
            ) / duration

            print(f"\nPeriod {index}")
            print(f"Start: {start_time}")
            print(f"End: {end_time}")
            print(f"Duration: {duration} candles")
            print(f"Maximum width: {maximum_width:.2f} ATR")
            print(f"Average width: {average_width:.2f} ATR")

    if rejected_results:
        print("\nFIRST FIVE REJECTIONS")

        for result in rejected_results[:5]:
            print(
                f"{result['timestamp']} | "
                f"Price: {result['market_price']:.2f} | "
                f"Width: {result['grid_width_atr']:.2f} ATR"
            )
