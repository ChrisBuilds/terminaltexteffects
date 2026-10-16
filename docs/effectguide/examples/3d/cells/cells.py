"""Cells: the same cube drawn with and without the tall-cell correction.

An Effect Guide example for the Tall Cells chapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.space3d import Cube, Shaded, Space3D
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.geometry3d import Camera


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
        """Make two spaces, one of them treating cells as square, and turn a cube in each."""
        super().__init__(effect)
        corrected = Space3D(self.terminal)
        # The same camera, except that it treats one row as one column tall.
        square = Space3D(self.terminal)
        square.camera = Camera.for_canvas(self.terminal.canvas, distance=square.camera.distance, row_scale=1.0)
        self.spaces = (corrected, square)
        for space, x in ((corrected, -20), (square, 20)):
            cube = space.body(Cube(16), at=(x, 0, 0)).draw(Shaded())
            cube.rotate("x", 20)
            cube.spin("y", turns=1, frames=300, ease=easing.in_out_sine)
        self.text_shown = False

    def __next__(self) -> str:
        """Turn the cubes, then swap them for the text."""
        if any(space.animating for space in self.spaces):
            for space in self.spaces:
                space.step()
        elif not self.text_shown:
            for space in self.spaces:
                for body in space.bodies:
                    body.erase()
                space.step()  # Hides the surface characters once nothing is drawn.
            for character in self.terminal.get_characters():
                self.terminal.set_character_visibility(character, is_visible=True)
            self.text_shown = True
        else:
            raise StopIteration
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
