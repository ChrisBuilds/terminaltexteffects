"""Tests for completion metadata exposed by custom argument validators."""

from __future__ import annotations

import argparse
import importlib
from typing import TYPE_CHECKING

import pytest

from terminaltexteffects.utils import argutils

if TYPE_CHECKING:
    from collections.abc import Callable


def test_completion_choices_are_valid_cli_values() -> None:
    """Every advertised completion choice should be accepted by its validator."""
    validators: tuple[tuple[tuple[str, ...], Callable[[str], object]], ...] = (
        (argutils.CharacterGroupArg.COMPLETION_CHOICES, argutils.CharacterGroupArg.type_parser),
        (argutils.CharacterSortArg.COMPLETION_CHOICES, argutils.CharacterSortArg.type_parser),
        (argutils.CharacterGroupOrSortArg.COMPLETION_CHOICES, argutils.CharacterGroupOrSortArg.type_parser),
        (argutils.ColorSortArg.COMPLETION_CHOICES, argutils.ColorSortArg.type_parser),
        (argutils.GradientDirection.COMPLETION_CHOICES, argutils.GradientDirection.type_parser),
        (argutils.Ease.COMPLETION_CHOICES, argutils.Ease.type_parser),
    )

    for choices, parser in validators:
        assert choices
        for choice in choices:
            parser(choice)


@pytest.mark.parametrize("shell", ["bash", "zsh"])
@pytest.mark.parametrize("combined", [False, True])
def test_character_sort_completion_generation(shell: str, *, combined: bool) -> None:
    """Sort and group-or-sort options advertise their full choice sets in both shells."""
    pytest.importorskip("shtab")
    generator = importlib.import_module("tools.generate_shell_completions")
    parser = argparse.ArgumentParser(prog="tte")
    validator = argutils.CharacterGroupOrSortArg if combined else argutils.CharacterSortArg
    action = parser.add_argument("--character-sort", type=validator.type_parser)
    expected = validator.COMPLETION_CHOICES
    for choice in expected:
        assert parser.parse_args(["--character-sort", choice]).character_sort is validator.type_parser(choice)

    generator._configure_completers(parser, ())
    assert action.choices == expected
    script = generator.shtab.complete(parser, shell=shell)
    assert f"({' '.join(expected)})" in script
