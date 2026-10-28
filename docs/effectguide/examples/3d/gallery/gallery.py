"""Gallery: every built-in shape, a few at a time.

An Effect Guide example for the Meshes chapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import Color, ColorPair, EffectCharacter, Shaded, Wireframe, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.shapes import (
    Box,
    Cube,
    Cylinder,
    Icosahedron,
    Octahedron,
    Prism,
    Pyramid,
    Shape,
    Sphere,
    Tetrahedron,
    Torus,
)
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.geometry import Coord


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "gallery", Gallery, GalleryConfig


@dataclass
class GalleryConfig(BaseConfig):
    """Configuration for the Gallery effect."""

    parser_spec = argutils.ParserSpec(
        name="gallery",
        help="Every built-in shape, a few at a time.",
        description="gallery | Every built-in shape, a few at a time.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c gallery --wireframe",
    )
    wireframe: bool = argutils.ArgSpec(
        name="--wireframe",
        default=False,
        action="store_true",
        help="Draw only the edges of the shapes.",
    )  # pyright: ignore[reportAssignmentType]
    "bool : Draw only the edges of the shapes."


PAGES = (
    (("Cube", Cube(18)), ("Box", Box(24, 12, 12)), ("Prism", Prism(sides=6, radius=11, height=16))),
    (
        ("Pyramid", Pyramid(sides=4, radius=12, height=18)),
        ("Tetrahedron", Tetrahedron(13)),
        ("Octahedron", Octahedron(13)),
    ),
    (("Icosahedron", Icosahedron(13)), ("Cylinder", Cylinder(radius=11, height=16))),
    (("Sphere", Sphere(13)), ("Torus", Torus(major_radius=10, minor_radius=4))),
)
"""The shapes and their names, a few at a time, so each is large enough to read as a shape on an 80 by 24 canvas."""


class GalleryIterator(BaseEffectIterator[GalleryConfig]):
    """Produce the frames of the Gallery effect."""

    def __init__(self, effect: Gallery) -> None:
        """Show the first page of shapes."""
        super().__init__(effect)
        self.world = self.terminal.world
        self.world.camera.set_perspective(0.5)
        self.look = Wireframe() if self.config.wireframe else Shaded()
        self.labels: list[EffectCharacter] = []
        self.pages = iter(PAGES)
        self.show_page(next(self.pages))
        self.text_shown = False

    def show_page(self, shapes: tuple[tuple[str, Shape], ...]) -> None:
        """Remove the shapes on screen and spin the next few, side by side, each named underneath."""
        for body in self.world.bodies:
            self.world.remove(body)  # Its cells are hidden when the world next paints.
        self.clear_labels()
        spacing = 27 if len(shapes) == 3 else 34
        for index, (name, shape) in enumerate(shapes):
            x = (index - (len(shapes) - 1) / 2) * spacing
            body = self.world.body(shape, at=(x, 0, 0)).draw(self.look)
            body.rotate("x", 25)
            body.spin("y", turns=1, frames=180, ease=easing.in_out_sine)
            self.label(name, self.terminal.canvas.center.column + round(x))

    def label(self, text: str, column: int) -> None:
        """Write `text` on the bottom row, centered on `column`. Labels are plain characters on the text plane."""
        start = column - len(text) // 2
        for offset, symbol in enumerate(text):
            character = self.terminal.add_character(symbol, Coord(start + offset, self.terminal.canvas.bottom))
            character.animation.set_appearance(symbol, ColorPair(fg=Color("#a0a0a0")))
            self.terminal.set_character_visibility(character, is_visible=True)
            self.labels.append(character)

    def clear_labels(self) -> None:
        """Hide the labels of the last page."""
        for character in self.labels:
            self.terminal.set_character_visibility(character, is_visible=False)
        self.labels.clear()

    def __next__(self) -> str:
        """Spin each page of shapes in turn, then swap them for the text."""
        if not self.world.animating:
            page = next(self.pages, None)
            if page is not None:
                self.show_page(page)
            elif self.text_shown:
                raise StopIteration
            else:
                for body in self.world.bodies:
                    self.world.remove(body)
                self.clear_labels()
                for character in self.terminal.get_characters():
                    self.terminal.set_character_visibility(character, is_visible=True)
                self.text_shown = True
        self.update()
        return self.frame


class Gallery(BaseEffect[GalleryConfig]):
    """Every built-in shape, a few at a time."""

    @property
    def _config_cls(self) -> type[GalleryConfig]:
        return GalleryConfig

    @property
    def _iterator_cls(self) -> type[GalleryIterator]:
        return GalleryIterator
