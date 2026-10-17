"""Surfaces: the same words mounted as characters on the left and drawn as a textured surface on the right.

An Effect Guide example for the Texture Mapping chapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import Color, ColorPair, EffectCharacter, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.space3d import Box, Space3D, Textured
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
        help="The same words mounted as characters and drawn as a textured surface.",
        description="surfaces | The same words mounted as characters and drawn as a textured surface.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c surfaces",
    )


WORDS = ("TERMINAL", "  TEXT  ", "EFFECTS ")
"""The words on both sides, one line each, padded to the same width so the texture repeats cleanly."""

LABEL = Color("#a0a0a0")


class SurfacesIterator(BaseEffectIterator[SurfacesConfig]):
    """Produce the frames of the Surfaces effect."""

    def __init__(self, effect: Surfaces) -> None:
        """Mount the words on one plane, texture them over a thin box, and turn both."""
        super().__init__(effect)
        self.space = Space3D(self.terminal)
        self.extras: list[EffectCharacter] = []
        center = self.terminal.canvas.center
        width, height = len(WORDS[0]), len(WORDS)

        # Left: one character per letter, mounted on a plane. Each keeps its own symbol and moves as a whole.
        self.sign = self.space.body(at=(-20, 0, 0))
        letters = []
        for row, line in enumerate(WORDS):
            for column, symbol in enumerate(line):
                if symbol == " ":
                    continue
                coord = Coord(center.column - 20 - width // 2 + column, center.row + height // 2 - row)
                letter = self.terminal.add_character(symbol, coord)
                letter.animation.set_appearance(symbol, ColorPair(fg=Color("#00D1FF")))
                letters.append(letter)
        self.sign.add_chars(letters, self.sign.text_plane(letters))
        for letter in letters:
            self.terminal.set_character_visibility(letter, is_visible=True)
            self.active_characters.add(letter)
        self.extras += letters

        # Right: a thin box with the same words as its texture. Each cell samples the text where it lands.
        self.panel = self.space.body(Box(width, height * 2, 1), at=(20, 0, 0)).draw(Textured("\n".join(WORDS)))

        for body in (self.sign, self.panel):
            body.rotate("x", 15)
            body.hold(30).spin("y", turns=1, frames=360, ease=easing.in_out_sine).hold(30)
        self.label("mounted", -20)
        self.label("textured", 20)
        self.text_shown = False

    def label(self, text: str, x: int) -> None:
        """Write `text` on the bottom row, under the body at `x`. Labels are plain characters, not part of the space."""
        start = self.terminal.canvas.center.column + x - len(text) // 2
        for offset, symbol in enumerate(text):
            character = self.terminal.add_character(symbol, Coord(start + offset, self.terminal.canvas.bottom))
            character.animation.set_appearance(symbol, ColorPair(fg=LABEL))
            self.terminal.set_character_visibility(character, is_visible=True)
            self.extras.append(character)

    def __next__(self) -> str:
        """Turn both, then swap them for the text."""
        if self.space.animating:
            self.space.step()
        elif not self.text_shown:
            self.sign.release_all()
            self.panel.erase()
            for character in self.extras:
                self.terminal.set_character_visibility(character, is_visible=False)
            self.space.step()  # Hides the surface characters once nothing is drawn.
            for character in self.terminal.get_characters():
                self.terminal.set_character_visibility(character, is_visible=True)
            self.text_shown = True
        else:
            raise StopIteration
        self.update()
        return self.frame


class Surfaces(BaseEffect[SurfacesConfig]):
    """The same words mounted as characters and drawn as a textured surface."""

    @property
    def _config_cls(self) -> type[SurfacesConfig]:
        return SurfacesConfig

    @property
    def _iterator_cls(self) -> type[SurfacesIterator]:
        return SurfacesIterator
