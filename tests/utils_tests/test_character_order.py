"""Tests for canonical character order normalization and compatibility inputs."""

from __future__ import annotations

from argparse import ArgumentTypeError
from typing import cast

import pytest

from terminaltexteffects import CharacterOrder
from terminaltexteffects.utils import argutils

pytestmark = [pytest.mark.utils, pytest.mark.smoke]


@pytest.mark.parametrize("order", CharacterOrder)
def test_character_order_normalizes_names_and_compatibility_enums(order: CharacterOrder) -> None:
    """Every advertised order has one canonical value across CLI and native inputs."""
    parser = argutils.CharacterOrderArg.type_parser
    assert parser(order) is order
    assert parser(order.name) is order
    assert parser(order.name.lower()) is order
    legacy_type = argutils.CharacterGroup if order.is_grouped else argutils.CharacterSort
    assert parser(legacy_type[order.name]) is order
    assert order.name.lower() in argutils.CharacterOrderArg.COMPLETION_CHOICES


@pytest.mark.parametrize("legacy", ["center_to_outside", "outside_to_center"])
def test_character_order_preserves_diamond_aliases(legacy: str) -> None:
    """Old diamond spellings normalize without becoming advertised options."""
    expected = CharacterOrder[f"DIAMONDS_{legacy.upper()}"]
    assert CharacterOrder[legacy.upper()] is expected
    assert argutils.CharacterOrderArg.type_parser(legacy) is expected
    assert legacy not in argutils.CharacterOrderArg.COMPLETION_CHOICES


@pytest.mark.parametrize("value", ["invalid", "", None, True, False, 1, [], {}, argutils.ColorSort.RANDOM])
def test_character_order_rejects_malformed_values(value: object) -> None:
    """Values are validated by type and name rather than coerced into enum numbers."""
    with pytest.raises(ArgumentTypeError):
        argutils.CharacterOrderArg.type_parser(cast("CharacterOrder", value))


def test_character_order_distinguishes_row_batches_from_individual_traversal() -> None:
    """Equal flat traversals retain distinct batching choices."""
    assert CharacterOrder.ROW_TOP_TO_BOTTOM.is_grouped
    assert not CharacterOrder.TOP_TO_BOTTOM_LEFT_TO_RIGHT.is_grouped
    assert not CharacterOrder.SPIRAL_CLOCKWISE.is_grouped
    assert set(argutils.CharacterOrderArg.COMPLETION_CHOICES) == {
        *argutils.CharacterGroupArg.COMPLETION_CHOICES,
        *argutils.CharacterSortArg.COMPLETION_CHOICES,
    }
