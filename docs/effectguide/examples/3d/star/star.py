"""Star: a custom star-shaped prism, built from its own mesh.

An Effect Guide example for the Meshes chapter.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from terminaltexteffects import Vec3, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.looks import Shaded, Wireframe
from terminaltexteffects.shapes import Shape
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.geometry3d import Face, Mesh


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "star", Star, StarConfig


@dataclass(frozen=True)
class StarPrism(Shape):
    """A star with `points` points, extruded `height` columns along the y axis."""

    points: int = 5
    outer: float = 16.0
    inner: float = 7.0
    height: float = 8.0

    def build_mesh(self) -> Mesh:
        """Return the star's mesh: one ring of corners at each end, joined by sides and capped."""
        corners = 2 * self.points
        ring = []
        for index in range(corners):
            # Corners alternate between the tips and the notches, going counterclockwise seen from above.
            radius = self.outer if index % 2 == 0 else self.inner
            angle = 2 * math.pi * index / corners
            ring.append((radius * math.sin(angle), radius * math.cos(angle)))
        half = self.height / 2
        bottom = [Vec3(x, -half, z) for x, z in ring]
        top = [Vec3(x, half, z) for x, z in ring]
        vertices = (*bottom, *top, Vec3(0, -half, 0), Vec3(0, half, 0))
        bottom_center, top_center = 2 * corners, 2 * corners + 1

        faces = []
        for index in range(corners):
            following = (index + 1) % corners
            # Each side is a rectangle. Listed counterclockwise seen from outside, its normal points out.
            faces.append(Face((index, following, corners + following, corners + index), tag=index))
        for index in range(corners):
            following = (index + 1) % corners
            # A star isn't convex, so each cap is a fan of triangles around its center.
            faces.append(Face((top_center, corners + index, corners + following), tag=corners))
            faces.append(Face((bottom_center, following, index), tag=corners + 1))
        return Mesh(vertices, tuple(faces))


@dataclass
class StarConfig(BaseConfig):
    """Configuration for the Star effect."""

    parser_spec = argutils.ParserSpec(
        name="star",
        help="A custom star-shaped prism, built from its own mesh.",
        description="star | A custom star-shaped prism, built from its own mesh.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c star --wireframe",
    )
    wireframe: bool = argutils.ArgSpec(
        name="--wireframe",
        default=False,
        action="store_true",
        help="Draw only the edges, which shows how the caps are split into triangles.",
    )  # pyright: ignore[reportAssignmentType]
    "bool : Draw only the edges, which shows how the caps are split into triangles."


class StarIterator(BaseEffectIterator[StarConfig]):
    """Produce the frames of the Star effect."""

    def __init__(self, effect: Star) -> None:
        """Stand the star up facing the viewer, and tumble it."""
        super().__init__(effect)
        self.world = self.terminal.world
        star = self.world.body(StarPrism()).draw(Wireframe() if self.config.wireframe else Shaded())
        star.rotate("x", -70)  # Stand the star up, with a cap facing the viewer and a point at the top.
        star.spin("y", turns=1, frames=360, ease=easing.in_out_sine)
        star.spin("x", turns=0.5, frames=360, ease=easing.in_out_sine, together=True)
        self.text_shown = False

    def __next__(self) -> str:
        """Tumble the star, then swap it for the text."""
        if not self.world.animating:
            if self.text_shown:
                raise StopIteration
            for body in self.world.bodies:
                body.erase()  # The world hides its cells when it next paints.
            for character in self.terminal.get_characters():
                self.terminal.set_character_visibility(character, is_visible=True)
            self.text_shown = True
        self.update()
        return self.frame


class Star(BaseEffect[StarConfig]):
    """A custom star-shaped prism, built from its own mesh."""

    @property
    def _config_cls(self) -> type[StarConfig]:
        return StarConfig

    @property
    def _iterator_cls(self) -> type[StarIterator]:
        return StarIterator
