"""Regression tests for multi-value argument normalization."""

from __future__ import annotations

import argparse

import pytest

from terminaltexteffects.effects.effect_rain import RainConfig
from terminaltexteffects.engine.base_config import FinalGradientStepsArg, FinalGradientStopsArg
from terminaltexteffects.utils.argutils import ArgSpec, PositiveInt, TupleAction
from terminaltexteffects.utils.graphics import Color

pytestmark = [pytest.mark.utils, pytest.mark.smoke]


@pytest.mark.parametrize("value", [[], ()])
def test_required_tuple_spec_rejects_empty_sequence(value: list[object] | tuple[()]) -> None:
    """A direct sequence must satisfy the minimum implied by `nargs="+"`."""
    with pytest.raises(argparse.ArgumentTypeError, match="at least one"):
        FinalGradientStopsArg().normalize(value)


@pytest.mark.parametrize("value", [[], ()])
def test_effect_config_rejects_empty_gradient_stops(value: list[object] | tuple[()]) -> None:
    """Invalid direct construction and assignment fail at the config boundary."""
    with pytest.raises(ValueError, match="final_gradient_stops"):
        RainConfig(final_gradient_stops=value)  # pyright: ignore[reportArgumentType]

    config = RainConfig()
    with pytest.raises(ValueError, match="final_gradient_stops"):
        config.final_gradient_stops = value  # pyright: ignore[reportAttributeAccessIssue]


def test_cli_requires_and_accepts_one_gradient_stop() -> None:
    """The CLI keeps its declared one-or-more value behavior."""
    parser = argparse.ArgumentParser()
    RainConfig._populate_parser(parser)

    with pytest.raises(SystemExit) as error:
        parser.parse_args(["--final-gradient-stops"])
    assert error.value.code == 2
    assert parser.parse_args(["--final-gradient-stops", "ff0000"]).final_gradient_stops == (Color("ff0000"),)


def test_scalar_and_optional_tuple_forms_remain_valid() -> None:
    """Canonical scalar defaults and optional empty sequences remain supported."""
    assert RainConfig().final_gradient_steps == 12
    assert FinalGradientStepsArg().normalize(8) == (8,)
    assert RainConfig(final_gradient_stops="ff0000").final_gradient_stops == (Color("ff0000"),)  # pyright: ignore[reportArgumentType]

    optional = ArgSpec(name="--numbers", default=(), type=PositiveInt.type_parser, nargs="*", action=TupleAction)
    assert optional.normalize([]) == ()
