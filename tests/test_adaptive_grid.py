
import pytest

from src.strategy.adaptive_grid import calculate_grid_levels


def test_default_grid_has_eleven_levels():
    levels = calculate_grid_levels(90_000, 110_000)

    assert len(levels) == 11
    assert levels[0] == 90_000
    assert levels[-1] == 110_000


def test_grid_has_equal_percentage_spacing():
    levels = calculate_grid_levels(90_000, 110_000)

    ratios = [
        levels[i + 1] / levels[i]
        for i in range(len(levels) - 1)
    ]

    for ratio in ratios:
        assert ratio == pytest.approx(ratios[0])


def test_custom_interval_count():
    levels = calculate_grid_levels(100, 200, intervals=4)

    assert len(levels) == 5
    assert levels[0] == 100
    assert levels[-1] == 200


@pytest.mark.parametrize(
    ("lower", "upper", "intervals"),
    [
        (0, 100, 10),
        (-10, 100, 10),
        (100, 100, 10),
        (110, 100, 10),
        (100, float("inf"), 10),
        (100, 200, 0),
        (100, 200, 2.5),
    ],
)
def test_invalid_inputs_are_rejected(lower, upper, intervals):
    with pytest.raises(ValueError):
        calculate_grid_levels(lower, upper, intervals)
