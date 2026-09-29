"""Test normalization of combined character group and sort arguments."""

from __future__ import annotations

from argparse import ArgumentTypeError
from typing import cast

import pytest

from terminaltexteffects.utils import argutils

pytestmark = [pytest.mark.utils, pytest.mark.smoke]


@pytest.mark.parametrize(
    ("canonical", "legacy"),
    [
        ("diamonds_center_to_outside", "center_to_outside"),
        ("diamonds_outside_to_center", "outside_to_center"),
    ],
)
def test_diamond_group_names_preserve_legacy_aliases(canonical: str, legacy: str) -> None:
    """Canonical diamond names retain enum values and accept legacy CLI spellings."""
    group = argutils.CharacterGroup[canonical.upper()]
    assert argutils.CharacterGroup[legacy.upper()] is group
    assert group.name.lower() == canonical
    assert group.value == (9 if canonical == "diamonds_center_to_outside" else 10)
    for validator in (argutils.CharacterGroupArg, argutils.CharacterGroupOrSortArg):
        assert canonical in validator.COMPLETION_CHOICES
        assert legacy not in validator.COMPLETION_CHOICES
        for spelling in (canonical, legacy, canonical.upper(), legacy.upper()):
            assert validator.type_parser(spelling) is group


@pytest.mark.parametrize("value", [*argutils.CharacterGroup, *argutils.CharacterSort])
def test_character_group_or_sort_accepts_cli_and_native_values(
    value: argutils.CharacterGroup | argutils.CharacterSort,
) -> None:
    """Every group and sort accepts both case-insensitive CLI text and its native enum."""
    validator = argutils.CharacterGroupOrSortArg
    assert validator.type_parser(value) is value
    assert validator.type_parser(value.name.lower()) is value
    assert validator.type_parser(value.name) is value
    assert value.name.lower() in validator.COMPLETION_CHOICES


@pytest.mark.parametrize("value", ["invalid", "", None, True, False, 1, [], {}, argutils.ColorSort.RANDOM])
def test_character_group_or_sort_rejects_invalid_values(value: object) -> None:
    """Malformed values and unrelated enums are rejected without coercion."""
    with pytest.raises(ArgumentTypeError):
        argutils.CharacterGroupOrSortArg.type_parser(
            cast("str | argutils.CharacterGroup | argutils.CharacterSort", value),
        )
