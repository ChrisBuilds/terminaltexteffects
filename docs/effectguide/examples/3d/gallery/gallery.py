"""Gallery: every built-in shape, turning in a grid.

An Effect Guide example for the Meshes chapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.space3d import (
    Box,
    Cube,
    Cylinder,
    Icosahedron,
    Octahedron,
    Prism,
    Pyramid,
    Shaded,
    Space3D,
    Sphere,
    Tetrahedron,
    Torus,
    Wireframe,
)
from terminaltexteffects.utils import argutils


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "gallery", Gallery, GalleryConfig


@dataclass
class GalleryConfig(BaseConfig):
    """Configuration for the Gallery effect."""

    parser_spec = argutils.ParserSpec(
        name="gallery",
        help="Every built-in shape, turning in a grid.",
        description="gallery | Every built-in shape, turning in a grid.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c gallery --wireframe",
    )
    wireframe: bool = argutils.ArgSpec(
        name="--wireframe",
        default=False,
        action="store_true",
        help="Draw only the edges of the shapes.",
    )  # pyright: ignore[reportAssignmentType]
    "bool : Draw only the edges of the shapes."


class GalleryIterator(BaseEffectIterator[GalleryConfig]):
    """Produce the frames of the Gallery effect."""

    def __init__(self, effect: Gallery) -> None:
        """Lay the shapes out in two rows of five and spin them."""
        super().__init__(effect)
        self.space = Space3D(self.terminal, perspective=0.5)
        shapes = [
            Cube(9),
            Box(12, 6, 6),
            Prism(sides=6, radius=5.5, height=8),
            Pyramid(sides=4, radius=6, height=9),
            Tetrahedron(6.5),
            Octahedron(6.5),
            Icosahedron(6.5),
            Cylinder(radius=5.5, height=8),
            Sphere(6.5),
            Torus(major_radius=5, minor_radius=2),
        ]
        look = Wireframe() if self.config.wireframe else Shaded()
        for index, shape in enumerate(shapes):
            row, column = divmod(index, 5)
            body = self.space.body(shape, at=(-32 + 16 * column, 11 - 24 * row, 0)).draw(look)
            body.rotate("x", 25)
            body.spin("y", turns=1, frames=360, ease=easing.in_out_sine)
        self.text_shown = False

    def __next__(self) -> str:
        """Spin the shapes, then swap them for the text."""
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


class Gallery(BaseEffect[GalleryConfig]):
    """Every built-in shape, turning in a grid."""

    @property
    def _config_cls(self) -> type[GalleryConfig]:
        return GalleryConfig

    @property
    def _iterator_cls(self) -> type[GalleryIterator]:
        return GalleryIterator
