"""Ticker: a message running around a turning cylinder, like a news ticker on a building.

An Effect Guide recipe.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import Color, Gradient, Ink, Textured, rotation_about
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.shapes import Cylinder
from terminaltexteffects.utils import argutils


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "ticker", Ticker, TickerConfig


@dataclass
class TickerConfig(BaseConfig):
    """Configuration for the Ticker effect."""

    parser_spec = argutils.ParserSpec(
        name="ticker",
        help="A message running around a turning cylinder.",
        description="ticker | A message running around a turning cylinder.",
        epilog='Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c ticker --message "HELLO "',
    )
    message: str = argutils.ArgSpec(
        name="--message",
        default=" TERMINAL TEXT EFFECTS ·",
        help="The message. It repeats around the cylinder.",
    )  # pyright: ignore[reportAssignmentType]
    "str : The message. It repeats around the cylinder."


class TickerIterator(BaseEffectIterator[TickerConfig]):
    """Produce the frames of the Ticker effect."""

    def __init__(self, effect: Ticker) -> None:
        """Wrap the message around a short, wide cylinder."""
        super().__init__(effect)
        # Gentle perspective keeps the front of the drum from magnifying the letters too much.
        self.world = self.terminal.world
        self.world.camera.set_perspective(0.5)
        self.world.set_light("front")
        amber = Gradient(Color("#3a2000"), Color("#ffb000"), Color("#fff0c0"), steps=10)
        # Two columns tall is one row, so the message runs around the drum once, in a single line.
        drum = Cylinder(radius=26, height=2, segments=72)
        self.drum = self.world.body(drum).draw(Textured(self.config.message, ink=Ink(amber)))
        self.tilt = rotation_about("x", 10)  # Tip the top toward the viewer, so we look down on the drum a little.
        self.frames = 420
        self.frame_number = 0
        self.text_shown = False

    def __next__(self) -> str:
        """Turn the drum a little each frame, then swap it for the text."""
        if self.frame_number < self.frames:
            # Turn about the drum's own axis first, then tilt. Calling rotate("y") on the tilted drum would turn it
            # about the world's y axis instead, and the drum would wobble.
            turn = rotation_about("y", -0.6 * self.frame_number)  # Right to left, so the message reads forward.
            self.drum.rotation = self.tilt * turn
            self.frame_number += 1
        elif not self.text_shown:
            self.drum.erase()  # The world hides its cells when it next paints.
            for character in self.terminal.get_characters():
                self.terminal.set_character_visibility(character, is_visible=True)
            self.text_shown = True
        else:
            raise StopIteration
        self.update()
        return self.frame


class Ticker(BaseEffect[TickerConfig]):
    """A message running around a turning cylinder."""

    @property
    def _config_cls(self) -> type[TickerConfig]:
        return TickerConfig

    @property
    def _iterator_cls(self) -> type[TickerIterator]:
        return TickerIterator
