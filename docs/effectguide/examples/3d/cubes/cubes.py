"""Cubes: three cubes of different sizes turn side by side, then the text appears.

An Effect Guide example for the 3D in a Terminal chapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.space3d import Cube, Shaded, Space3D, Wireframe
from terminaltexteffects.utils import argutils


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "cubes", Cubes, CubesConfig


@dataclass
class CubesConfig(BaseConfig):
    """Configuration for the Cubes effect."""

    parser_spec = argutils.ParserSpec(
        name="cubes",
        help="Three cubes of different sizes turn side by side.",
        description="cubes | Three cubes of different sizes turn side by side.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c cubes --wireframe",
    )
    wireframe: bool = argutils.ArgSpec(
        name="--wireframe",
        default=False,
        action="store_true",
        help="Draw only the edges of the cubes.",
    )  # pyright: ignore[reportAssignmentType]
    "bool : Draw only the edges of the cubes."


class CubesIterator(BaseEffectIterator[CubesConfig]):
    """Produce the frames of the Cubes effect."""

    def __init__(self, effect: Cubes) -> None:
        """Place three cubes and queue their turns."""
        super().__init__(effect)
        self.space = Space3D(self.terminal)
        look = Wireframe() if self.config.wireframe else Shaded()
        for size, x in ((6, -28), (12, -10), (24, 18)):
            cube = self.space.body(Cube(size), at=(x, 0, 0)).draw(look)
            cube.rotate("x", 20)
            cube.spin("y", turns=1, frames=240, ease=easing.in_out_sine)
        self.text_shown = False

    def __next__(self) -> str:
        """Turn the cubes, then swap them for the text."""
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


class Cubes(BaseEffect[CubesConfig]):
    """Three cubes of different sizes turn side by side."""

    @property
    def _config_cls(self) -> type[CubesConfig]:
        return CubesConfig

    @property
    def _iterator_cls(self) -> type[CubesIterator]:
        return CubesIterator
