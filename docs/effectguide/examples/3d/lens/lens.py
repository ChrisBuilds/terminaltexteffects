"""Lens: three cubes running away from the viewer, seen with a chosen perspective.

An Effect Guide example for the Camera and Projection chapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.space3d import Cube, Shaded, Space3D
from terminaltexteffects.utils import argutils


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "lens", Lens, LensConfig


@dataclass
class LensConfig(BaseConfig):
    """Configuration for the Lens effect."""

    parser_spec = argutils.ParserSpec(
        name="lens",
        help="Three cubes running away from the viewer.",
        description="lens | Three cubes running away from the viewer.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c lens --perspective 2",
    )
    perspective: float = argutils.ArgSpec(
        name="--perspective",
        type=argutils.NonNegativeFloat.type_parser,
        default=1.0,
        metavar=argutils.NonNegativeFloat.METAVAR,
        help="1 is natural, larger values exaggerate depth, and 0 is a flat orthographic view.",
    )  # pyright: ignore[reportAssignmentType]
    "float : 1 is natural, larger values exaggerate depth, and 0 is a flat orthographic view."


class LensIterator(BaseEffectIterator[LensConfig]):
    """Produce the frames of the Lens effect."""

    def __init__(self, effect: Lens) -> None:
        """Place three cubes from near and left to far and right, and spin them."""
        super().__init__(effect)
        self.space = Space3D(self.terminal, perspective=self.config.perspective)
        # Each cube is 26 columns right of and 60 columns farther away than the one before it.
        for x, z in ((-26, 0), (0, -60), (26, -120)):
            cube = self.space.body(Cube(14), at=(x, 0, z)).draw(Shaded())
            cube.rotate("x", 20)
            cube.spin("y", turns=1, frames=240, ease=easing.in_out_sine)
        self.text_shown = False

    def __next__(self) -> str:
        """Spin the cubes, then swap them for the text."""
        if self.space.animating:
            self.space.step()
        elif not self.text_shown:
            for body in self.space.bodies:
                body.erase()
            self.space.step()  # Hides the surface characters once nothing is drawn.
            for character in self.terminal.get_characters():
                self.terminal.set_character_visibility(character, is_visible=True)
            self.text_shown = True
        else:
            raise StopIteration
        self.update()
        return self.frame


class Lens(BaseEffect[LensConfig]):
    """Three cubes running away from the viewer."""

    @property
    def _config_cls(self) -> type[LensConfig]:
        return LensConfig

    @property
    def _iterator_cls(self) -> type[LensIterator]:
        return LensIterator
