
from src.backtesting.grid_stability import calculate_grid_stability


def make_active_result(
    lower,
    upper,
    spacing=1.0,
):
    return {
        "status": "active",
        "lower_bound": lower,
        "upper_bound": upper,
        "grid_width": upper - lower,
        "percentage_spacing": spacing,
    }


def make_rejected_result():
    return {
        "status": "rejected",
    }


def test_stability_calculates_boundary_movement():
    results = [
        make_active_result(100, 200),
        make_active_result(110, 220),
    ]

    report = calculate_grid_stability(results)

    assert report["average_upper_boundary_movement"] == 20
    assert report["average_lower_boundary_movement"] == 10


def test_stability_calculates_width_and_centre_movement():
    results = [
        make_active_result(100, 200),
        make_active_result(110, 220),
    ]

    report = calculate_grid_stability(results)

    assert report["average_grid_width_change"] == 10
    assert report["average_grid_centre_movement"] == 15


def test_stability_calculates_spacing_movement():
    results = [
        make_active_result(100, 200, 1.0),
        make_active_result(110, 220, 1.5),
    ]

    report = calculate_grid_stability(results)

    assert report["average_spacing_change"] == 0.5


def test_rejected_grid_interrupts_stability_comparison():
    results = [
        make_active_result(100, 200),
        make_rejected_result(),
        make_active_result(110, 220),
    ]

    report = calculate_grid_stability(results)

    assert report["consecutive_active_transitions"] == 0
    assert report["interrupted_transitions"] == 2
    assert report["rejected_calculations"] == 1


def test_stability_handles_empty_results():
    report = calculate_grid_stability([])

    assert report["total_calculations"] == 0
    assert report["active_calculations"] == 0
    assert report["average_grid_centre_movement"] == 0


def test_stability_handles_one_active_grid():
    results = [
        make_active_result(100, 200),
    ]

    report = calculate_grid_stability(results)

    assert report["consecutive_active_transitions"] == 0
    assert report["maximum_grid_centre_movement"] == 0
