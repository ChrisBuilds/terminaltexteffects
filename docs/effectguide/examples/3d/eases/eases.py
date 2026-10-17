"""Eases: three cubes make the same turn with different easing functions.

An Effect Guide example for the Animating in 3D chapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import Color, ColorPair, EffectCharacter, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.space3d import Cube, Shaded, Space3D
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.geometry import Coord


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "eases", Eases, EasesConfig


@dataclass
class EasesConfig(BaseConfig):
    """Configuration for the Eases effect."""

    parser_spec = argutils.ParserSpec(
        name="eases",
        help="Three cubes make the same turn with different easing functions.",
        description="eases | Three cubes make the same turn with different easing functions.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c eases",
    )


EASES = (("linear", None), ("in_out_sine", easing.in_out_sine), ("out_back", easing.out_back))
"""Each cube's label and easing function. `None` is linear: the turn moves at one speed from start to end."""


class EasesIterator(BaseEffectIterator[EasesConfig]):
    """Produce the frames of the Eases effect."""

    def __init__(self, effect: Eases) -> None:
        """Queue the same quarter turns on each cube, eased differently."""
        super().__init__(effect)
        self.space = Space3D(self.terminal)
        self.labels: list[EffectCharacter] = []
        for index, (name, ease) in enumerate(EASES):
            x = (index - 1) * 26
            cube = self.space.body(Cube(14), at=(x, 0, 0)).draw(Shaded())
            cube.rotate("x", 20)
            # Four quarter turns with a pause between them, so each start and stop is easy to watch.
            for _ in range(4):
                cube.hold(30).spin("y", turns=0.25, frames=60, ease=ease)
            cube.hold(30)
            self.label(name, x)
        self.text_shown = False

    def label(self, text: str, x: int) -> None:
        """Write `text` on the bottom row, under the body at `x`. Labels are plain characters, not part of the space."""
        start = self.terminal.canvas.center.column + x - len(text) // 2
        for offset, symbol in enumerate(text):
            character = self.terminal.add_character(symbol, Coord(start + offset, self.terminal.canvas.bottom))
            character.animation.set_appearance(symbol, ColorPair(fg=Color("#a0a0a0")))
            self.terminal.set_character_visibility(character, is_visible=True)
            self.labels.append(character)

    def __next__(self) -> str:
        """Play the turns, then swap the cubes for the text."""
        if self.space.animating:
            self.space.step()
        elif not self.text_shown:
            for body in self.space.bodies:
                body.erase()
            for character in self.labels:
                self.terminal.set_character_visibility(character, is_visible=False)
            self.space.step()  # Hides the surface characters once nothing is drawn.
            for character in self.terminal.get_characters():
                self.terminal.set_character_visibility(character, is_visible=True)
            self.text_shown = True
        else:
            raise StopIteration
        self.update()
        return self.frame


class Eases(BaseEffect[EasesConfig]):
    """Three cubes make the same turn with different easing functions."""

    @property
    def _config_cls(self) -> type[EasesConfig]:
        return EasesConfig

    @property
    def _iterator_cls(self) -> type[EasesIterator]:
        return EasesIterator
