"""Regression tests for positive float range validation."""

from __future__ import annotations

from argparse import ArgumentTypeError

import pytest

from terminaltexteffects.effects.effect_rain import RainConfig
from terminaltexteffects.utils.argutils import PositiveFloatRange

pytestmark = [pytest.mark.utils, pytest.mark.smoke]


@pytest.mark.parametrize("value", [(-2.0, -1.0), (-1.0, 1.0), [-1.0, -0.5], [0.0, 1.0]])
def test_native_range_rejects_nonpositive_endpoints(value: tuple[float, float] | list[float]) -> None:
    """Native tuples and lists must contain positive endpoints."""
    with pytest.raises(ArgumentTypeError, match="start > 0"):
        PositiveFloatRange.type_parser(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [("0.1-0.1", (0.1, 0.1)), ((0.1, 0.1), (0.1, 0.1)), ([0.1, 1], (0.1, 1.0))],
)
def test_range_accepts_positive_endpoints(
    value: str | tuple[float, float] | list[float], expected: tuple[float, float],
) -> None:
    """CLI strings and native ranges retain valid inclusive endpoints."""
    assert PositiveFloatRange.type_parser(value) == expected


def test_effect_config_rejects_negative_movement_speed_range() -> None:
    """Effect configs reject invalid ranges on construction and assignment."""
    with pytest.raises(ValueError, match="movement_speed"):
        RainConfig(movement_speed=(-2.0, -1.0))

    config = RainConfig()
    with pytest.raises(ValueError, match="movement_speed"):
        config.movement_speed = (-1.0, 1.0)
