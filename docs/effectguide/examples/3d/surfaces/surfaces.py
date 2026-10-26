"""Surfaces: the same words attached as characters on the left and drawn as a textured surface on the right.

An Effect Guide example for the Texture Mapping chapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import Color, ColorPair, EffectCharacter, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.drawing import Textured
from terminaltexteffects.engine.shapes import Box
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.geometry import Coord


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "surfaces", Surfaces, SurfacesConfig


@dataclass
class SurfacesConfig(BaseConfig):
    """Configuration for the Surfaces effect."""

    parser_spec = argutils.ParserSpec(
        name="surfaces",
        help="The same words attached as characters and drawn as a textured surface.",
        description="surfaces | The same words attached as characters and drawn as a textured surface.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c surfaces",
    )


WORDS = ("TERMINAL", "  TEXT  ", "EFFECTS ")
"""The words on both sides, one line each, padded to the same width so the texture repeats cleanly."""

LABEL = Color("#a0a0a0")


class SurfacesIterator(BaseEffectIterator[SurfacesConfig]):
    """Produce the frames of the Surfaces effect."""

    def __init__(self, effect: Surfaces) -> None:
        """Attach the words to one body, texture them over a thin box, and turn both."""
        super().__init__(effect)
        self.world = self.terminal.world
        self.extras: list[EffectCharacter] = []
        center = self.terminal.canvas.center
        width, height = len(WORDS[0]), len(WORDS)

        # Left: one character per letter, attached to a body with no shape. Each keeps its own symbol and moves as
        # a whole.
        self.sign = self.world.body(at=(-20, 0, 0))
        letters: list[EffectCharacter] = []
        for row, line in enumerate(WORDS):
            for column, symbol in enumerate(line):
                if symbol == " ":
                    continue
                coord = Coord(center.column - 20 - width // 2 + column, center.row + height // 2 - row)
                letter = self.terminal.add_character(symbol, coord)
                letter.animation.set_appearance(symbol, ColorPair(fg=Color("#00D1FF")))
                letters.append(letter)
        for letter in letters:
            letter.attach(self.sign)  # Without `at`, it stays where it is: on its cell until the body moves.
            self.terminal.set_character_visibility(letter, is_visible=True)
            self.active_characters.add(letter)
        self.extras += letters

        # Right: a thin box with the same words as its texture. Each cell samples the text where it lands.
        self.panel = self.world.body(Box(width, height * 2, 1), at=(20, 0, 0)).draw(Textured("\n".join(WORDS)))

        for body in (self.sign, self.panel):
            body.rotate("x", 15)
            body.hold(30).spin("y", turns=1, frames=360, ease=easing.in_out_sine).hold(30)
        self.label("attached", -20)
        self.label("textured", 20)
        self.text_shown = False

    def label(self, text: str, x: int) -> None:
        """Write `text` on the bottom row, under the body at `x`. Labels are plain characters on the text plane."""
        start = self.terminal.canvas.center.column + x - len(text) // 2
        for offset, symbol in enumerate(text):
            character = self.terminal.add_character(symbol, Coord(start + offset, self.terminal.canvas.bottom))
            character.animation.set_appearance(symbol, ColorPair(fg=LABEL))
            self.terminal.set_character_visibility(character, is_visible=True)
            self.extras.append(character)

    def __next__(self) -> str:
        """Turn both, then swap them for the text."""
        if not self.world.animating:
            if self.text_shown:
                raise StopIteration
            self.panel.erase()  # The world hides its cells when it next paints.
            for character in self.extras:
                self.terminal.set_character_visibility(character, is_visible=False)
            for character in self.terminal.get_characters():
                self.terminal.set_character_visibility(character, is_visible=True)
            self.text_shown = True
        self.update()
        return self.frame


class Surfaces(BaseEffect[SurfacesConfig]):
    """The same words attached as characters and drawn as a textured surface."""

    @property
    def _config_cls(self) -> type[SurfacesConfig]:
        return SurfacesConfig

    @property
    def _iterator_cls(self) -> type[SurfacesIterator]:
        return SurfacesIterator
