"""Cells: the same cube drawn with and without the tall-cell correction.

An Effect Guide example for the Tall Cells chapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.drawing import Shaded
from terminaltexteffects.engine.shapes import Box, Cube
from terminaltexteffects.utils import argutils


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "cells", Cells, CellsConfig


@dataclass
class CellsConfig(BaseConfig):
    """Configuration for the Cells effect."""

    parser_spec = argutils.ParserSpec(
        name="cells",
        help="The same cube drawn with and without the tall-cell correction.",
        description="cells | The same cube drawn with and without the tall-cell correction.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c cells",
    )


class CellsIterator(BaseEffectIterator[CellsConfig]):
    """Produce the frames of the Cells effect."""

    def __init__(self, effect: Cells) -> None:
        """Turn a cube beside a box twice its height: how the cube would look if rows counted as one unit."""
        super().__init__(effect)
        self.world = self.terminal.world
        # The camera counts a row as two units tall, so the cube on the left is square on screen. Treating rows
        # as one unit would draw everything twice as tall, like the box on the right.
        self.bodies = (
            self.world.body(Cube(16), at=(-20, 0, 0)).draw(Shaded()),
            self.world.body(Box(16, 32, 16), at=(20, 0, 0)).draw(Shaded()),
        )
        for body in self.bodies:
            body.rotate("x", 20)
            body.spin("y", turns=1, frames=300, ease=easing.in_out_sine)
        self.text_shown = False

    def __next__(self) -> str:
        """Turn the bodies, then swap them for the text."""
        if not self.world.animating:
            if self.text_shown:
                raise StopIteration
            for body in self.bodies:
                body.erase()  # The world hides its cells when it next paints.
            for character in self.terminal.get_characters():
                self.terminal.set_character_visibility(character, is_visible=True)
            self.text_shown = True
        self.update()
        return self.frame


class Cells(BaseEffect[CellsConfig]):
    """The same cube drawn with and without the tall-cell correction."""

    @property
    def _config_cls(self) -> type[CellsConfig]:
        return CellsConfig

    @property
    def _iterator_cls(self) -> type[CellsIterator]:
        return CellsIterator
