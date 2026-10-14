"""Tests for the MySpray effect."""

from __future__ import annotations

import re
import typing

import pytest
from myspray import MySpray

from terminaltexteffects.utils.exceptions.terminal_exceptions import EmptyInputError

Position = typing.Literal["n", "ne", "e", "se", "s", "sw", "w", "nw", "center"]
ANSI_ESCAPE = re.compile(r"\x1b(\[[0-?]*[ -/]*[@-~]|[78])")
INPUTS = {
    "single character": "x",
    "one row": "Hello, world",
    "one column": "a\nb\nc",
    "sparse": "a\n\n\n          b",
    "wide characters": "漢字テスト",
    "tabs": "a\tb\tc",
}


def play(effect: MySpray) -> str:
    """Run the effect without a terminal or frame-rate delay, and return its last frame."""
    effect.terminal_config.frame_rate = 0
    effect.terminal_config.ignore_terminal_dimensions = True
    frames = list(effect)
    return frames[-1] if frames else ""


@pytest.mark.parametrize("text", INPUTS.values(), ids=INPUTS.keys())
def test_ends_with_the_input_text(text: str) -> None:
    """The last frame shows every line of the input."""
    effect = MySpray(text)
    effect.terminal_config.tab_width = 1
    last_frame = ANSI_ESCAPE.sub("", play(effect))
    for line in text.replace("\t", " ").splitlines():
        assert line.strip() in last_frame


def test_empty_input_is_rejected_by_the_engine() -> None:
    """Input with no visible characters never reaches the effect."""
    with pytest.raises(EmptyInputError):
        play(MySpray(""))


@pytest.mark.parametrize("position", typing.get_args(Position))
def test_every_spray_position_on_a_larger_canvas(position: Position) -> None:
    """Every spray position works when the canvas is larger than the text."""
    effect = MySpray("Hello")
    effect.effect_config.spray_position = position
    effect.terminal_config.canvas_width = 20
    effect.terminal_config.canvas_height = 5
    assert "Hello" in ANSI_ESCAPE.sub("", play(effect))


def test_dynamic_color_handling_keeps_input_colors() -> None:
    """With dynamic color handling, characters end in their input colors."""
    effect = MySpray("\x1b[38;2;255;0;0mRed\x1b[0m")
    effect.terminal_config.existing_color_handling = "dynamic"
    assert "38;2;255;0;0" in play(effect)
