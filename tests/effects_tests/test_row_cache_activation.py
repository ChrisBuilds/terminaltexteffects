"""Protect measured cache activation ranges across the opted-in effects."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

import pytest

from terminaltexteffects.effects import (
    effect_bouncyballs,
    effect_errorcorrect,
    effect_pour,
    effect_print,
    effect_rain,
    effect_synthgrid,
)
from terminaltexteffects.engine.terminal import Terminal, TerminalConfig

if TYPE_CHECKING:
    from terminaltexteffects.engine.base_effect import BaseEffect

EFFECTS: dict[str, type[BaseEffect[Any]]] = {
    "print": effect_print.Print,
    "pour": effect_pour.Pour,
    "bouncyballs": effect_bouncyballs.BouncyBalls,
    "errorcorrect": effect_errorcorrect.ErrorCorrect,
    "synthgrid": effect_synthgrid.SynthGrid,
    "rain": effect_rain.Rain,
}


def _input(width: int, height: int, style: str) -> str:
    if style == "sparse":
        return f"A\x1b[{height};{width}HB"
    if style == "wide":
        return "\n".join(["A" * (width - 2) + "界"] * height)
    numerator = {"dense": 8, "half": 4, "three_quarters": 6, "seven_eighths": 7}[style]
    return "\n".join(
        "".join("A" if (row + column) % 8 < numerator else " " for column in range(width))
        for row in range(height)
    )


def _effect(name: str, width: int, height: int, style: str) -> BaseEffect[Any]:
    effect = EFFECTS[name](_input(width, height, style))
    config = TerminalConfig._build_config()
    config.frame_rate = 0
    config.ignore_terminal_dimensions = True
    config.canvas_width = width
    config.canvas_height = height
    effect.terminal_config = config
    return effect


@pytest.mark.parametrize(
    ("name", "width", "height", "style", "enabled"),
    [
        ("print", 32, 8, "dense", True),
        ("print", 31, 8, "dense", False),
        ("print", 16, 16, "dense", True),
        ("print", 15, 18, "dense", False),
        ("print", 64, 3, "dense", False),
        ("print", 24, 24, "dense", True),
        ("print", 80, 24, "sparse", False),
        ("print", 80, 24, "wide", False),
        ("print", 128, 1, "dense", False),
        ("errorcorrect", 8, 10, "dense", True),
        ("errorcorrect", 8, 9, "dense", False),
        ("errorcorrect", 7, 12, "dense", False),
        ("errorcorrect", 64, 4, "dense", False),
        ("errorcorrect", 17, 5, "dense", True),
        ("errorcorrect", 80, 24, "sparse", False),
        ("errorcorrect", 80, 24, "wide", False),
        ("synthgrid", 8, 4, "dense", True),
        ("synthgrid", 7, 4, "dense", False),
        ("synthgrid", 8, 3, "dense", False),
        ("synthgrid", 80, 24, "sparse", True),
        ("synthgrid", 80, 24, "wide", False),
        ("synthgrid", 1, 80, "dense", False),
        ("synthgrid", 80, 1, "dense", False),
        ("pour", 64, 12, "dense", True),
        ("pour", 63, 13, "dense", False),
        ("pour", 80, 11, "dense", False),
        ("pour", 64, 24, "three_quarters", True),
        ("pour", 80, 24, "half", False),
        ("pour", 80, 24, "sparse", False),
        ("pour", 80, 24, "wide", False),
        ("bouncyballs", 64, 16, "dense", True),
        ("bouncyballs", 63, 18, "dense", False),
        ("bouncyballs", 80, 15, "dense", False),
        ("bouncyballs", 64, 24, "three_quarters", True),
        ("bouncyballs", 80, 24, "half", False),
        ("bouncyballs", 80, 24, "three_quarters", True),
        ("bouncyballs", 80, 24, "sparse", False),
        ("bouncyballs", 80, 24, "wide", False),
        ("rain", 80, 24, "dense", True),
        ("rain", 80, 24, "seven_eighths", True),
        ("rain", 80, 24, "three_quarters", False),
        ("rain", 79, 24, "dense", False),
        ("rain", 80, 23, "dense", False),
        ("rain", 64, 24, "dense", False),
        ("rain", 80, 24, "sparse", False),
        ("rain", 80, 24, "wide", False),
    ],
)
def test_effect_row_cache_selection(name: str, width: int, height: int, style: str, *, enabled: bool) -> None:
    """Caching follows measured size, occupancy and display-width requirements."""
    iterator = iter(_effect(name, width, height, style))
    assert (iterator.terminal._row_cache is not None) is enabled


@pytest.mark.parametrize("name", ["print", "pour", "bouncyballs", "errorcorrect", "rain"])
def test_effect_row_cache_skips_clipped_text(name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """A large logical canvas does not opt in when the terminal shows only three rows."""
    effect = _effect(name, 80, 24, "dense")
    effect.terminal_config.ignore_terminal_dimensions = False
    monkeypatch.setattr(Terminal, "_get_terminal_dimensions", lambda _self: (80, 3))
    iterator = iter(effect)
    assert iterator.terminal._row_cache is None


@pytest.mark.parametrize(("direction", "enabled"), [("up", True), ("down", True), ("left", False), ("right", False)])
def test_pour_row_cache_direction(direction: Literal["up", "down", "left", "right"], *, enabled: bool) -> None:
    """Horizontal pouring retains ordinary rendering because caching regressed its timing."""
    effect = effect_pour.Pour(_input(80, 24, "dense"))
    effect.terminal_config = _effect("pour", 80, 24, "dense").terminal_config
    effect.effect_config.pour_direction = direction
    iterator = iter(effect)
    assert (iterator.terminal._row_cache is not None) is enabled


@pytest.mark.parametrize("name", list(EFFECTS))
def test_effect_row_cache_handles_later_width_transitions(name: str) -> None:
    """An opted-in effect still matches ordinary rendering after a visual becomes wide."""
    iterator = iter(_effect(name, 80, 24, "dense"))
    terminal = iterator.terminal
    cache = terminal._row_cache
    assert cache is not None
    character = terminal.get_characters()[0]
    character.motion.set_coordinate(character.input_coord)
    terminal.set_character_visibility(character, is_visible=True)

    for symbol in ("A", "界", "A"):
        character.animation.set_appearance(symbol)
        output = terminal.get_formatted_output_string()
        terminal._row_cache = None
        try:
            reference = terminal.get_formatted_output_string()
        finally:
            terminal._row_cache = cache
        assert output == reference
