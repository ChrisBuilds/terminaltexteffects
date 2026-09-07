"""Tests for completion metadata exposed by custom argument validators."""

from __future__ import annotations

from typing import TYPE_CHECKING

from terminaltexteffects.utils import argutils

if TYPE_CHECKING:
    from collections.abc import Callable


def test_completion_choices_are_valid_cli_values() -> None:
    """Every advertised completion choice should be accepted by its validator."""
    validators: tuple[tuple[tuple[str, ...], Callable[[str], object]], ...] = (
        (argutils.CharacterGroupArg.COMPLETION_CHOICES, argutils.CharacterGroupArg.type_parser),
        (argutils.CharacterSortArg.COMPLETION_CHOICES, argutils.CharacterSortArg.type_parser),
        (argutils.ColorSortArg.COMPLETION_CHOICES, argutils.ColorSortArg.type_parser),
        (argutils.GradientDirection.COMPLETION_CHOICES, argutils.GradientDirection.type_parser),
        (argutils.Ease.COMPLETION_CHOICES, argutils.Ease.type_parser),
    )

    for choices, parser in validators:
        assert choices
        for choice in choices:
            parser(choice)
