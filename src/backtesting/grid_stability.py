
from src.backtesting.grid_behavior import simulate_grid_behavior


def calculate_grid_stability(results: list[dict]) -> dict:
    """
    Analyse how much the adaptive grid changes between calculations.

    Only consecutive active grids are compared. Rejected calculations
    interrupt the comparison so that outages are not treated as stability.
    """

    active_results = [
        result
        for result in results
        if result["status"] == "active"
    ]

    rejected_count = sum(
        1 for result in results
        if result["status"] == "rejected"
    )

    boundary_changes = []
    width_changes = []
    centre_changes = []
    spacing_changes = []
    centre_movement_details = []

    interrupted_transitions = 0

    for previous, current in zip(results, results[1:]):

        if (
            previous["status"] != "active"
            or current["status"] != "active"
        ):
            interrupted_transitions += 1
            continue

        previous_centre = (
            previous["upper_bound"] + previous["lower_bound"]
        ) / 2

        current_centre = (
            current["upper_bound"] + current["lower_bound"]
        ) / 2

        centre_change = current_centre - previous_centre

        centre_changes.append(centre_change)

        centre_movement_details.append({
            "previous_timestamp": previous.get("timestamp", "N/A"),
            "current_timestamp": current.get("timestamp", "N/A"),
            "previous_centre": previous_centre,
            "current_centre": current_centre,
            "movement": abs(centre_change),
            "previous_market_price": previous.get("market_price", "N/A"),
            "current_market_price": current.get("market_price", "N/A"),
        })

        boundary_changes.append({
            "upper": current["upper_bound"] - previous["upper_bound"],
            "lower": current["lower_bound"] - previous["lower_bound"],
        })

        width_changes.append(
            current["grid_width"] - previous["grid_width"]
        )

        spacing_changes.append(
            current["percentage_spacing"]
            - previous["percentage_spacing"]
        )

    def average_absolute(values):
        if not values:
            return 0.0

        return sum(abs(value) for value in values) / len(values)

    upper_changes = [
        change["upper"] for change in boundary_changes
    ]

    lower_changes = [
        change["lower"] for change in boundary_changes
    ]

    return {
        "total_calculations": len(results),
        "active_calculations": len(active_results),
        "rejected_calculations": rejected_count,
        "consecutive_active_transitions": len(width_changes),
        "interrupted_transitions": interrupted_transitions,

        "average_upper_boundary_movement": average_absolute(
            upper_changes
        ),

        "average_lower_boundary_movement": average_absolute(
            lower_changes
        ),

        "average_grid_width_change": average_absolute(
            width_changes
        ),

        "average_grid_centre_movement": average_absolute(
            centre_changes
        ),

        "average_spacing_change": average_absolute(
            spacing_changes
        ),

        "maximum_grid_centre_movement": (
            max(abs(value) for value in centre_changes)
            if centre_changes else 0.0
        ),
        
        "largest_grid_centre_movement": (
            max(
                centre_movement_details,
                key=lambda item: item["movement"]
            )
            if centre_movement_details else None
        ),
    }


if __name__ == "__main__":
    results = simulate_grid_behavior(
        config_path="config/strategy_36.json"
    )

    report = calculate_grid_stability(results)

    print("\nADAPTIVE GRID STABILITY REPORT")
    print("--------------------------------")

    print(f"Total calculations: {report['total_calculations']}")
    print(f"Active calculations: {report['active_calculations']}")
    print(f"Rejected calculations: {report['rejected_calculations']}")

    print(
        "Consecutive active transitions: "
        f"{report['consecutive_active_transitions']}"
    )

    print(
        "Interrupted transitions: "
        f"{report['interrupted_transitions']}"
    )

    print("\nBOUNDARY MOVEMENT")
    print("-----------------")

    print(
        "Average upper boundary movement: "
        f"{report['average_upper_boundary_movement']:.2f} USDT"
    )

    print(
        "Average lower boundary movement: "
        f"{report['average_lower_boundary_movement']:.2f} USDT"
    )

    print("\nGRID MOVEMENT")
    print("-------------")

    print(
        "Average grid width change: "
        f"{report['average_grid_width_change']:.2f} USDT"
    )

    print(
        "Average grid centre movement: "
        f"{report['average_grid_centre_movement']:.2f} USDT"
    )

    print(
        "Maximum grid centre movement: "
        f"{report['maximum_grid_centre_movement']:.2f} USDT"
    )
    
    largest_movement = report["largest_grid_centre_movement"]

    if largest_movement:
        print("\nLARGEST GRID REPOSITIONING")
        print("-------------------------")
        print(
            f"Previous timestamp: "
            f"{largest_movement['previous_timestamp']}"
        )
        print(
            f"Current timestamp: "
            f"{largest_movement['current_timestamp']}"
        )
        print(
            f"Previous centre: "
            f"{largest_movement['previous_centre']:.2f}"
        )
        print(
            f"Current centre: "
            f"{largest_movement['current_centre']:.2f}"
        )
        print(
            f"Movement: "
            f"{largest_movement['movement']:.2f} USDT"
        )
        print(
            f"Previous market price: "
            f"{largest_movement['previous_market_price']:.2f}"
        )
        print(
            f"Current market price: "
            f"{largest_movement['current_market_price']:.2f}"
        )

    print("\nSPACING STABILITY")
    print("-----------------")

    print(
        "Average spacing change: "
        f"{report['average_spacing_change']:.6f} percentage points"
    )
