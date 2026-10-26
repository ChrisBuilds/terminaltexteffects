"""Depth: a sphere passes through a cube, or a cube shows its far side through its text.

An Effect Guide example for the Depth and Hidden Surfaces chapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.drawing import Shaded, Textured
from terminaltexteffects.engine.shapes import Cube, Sphere
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.geometry3d import Vec3


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "depth", Depth, DepthConfig


@dataclass
class DepthConfig(BaseConfig):
    """Configuration for the Depth effect."""

    parser_spec = argutils.ParserSpec(
        name="depth",
        help="A sphere passes through a cube, or a cube shows its far side through its text.",
        description="depth | A sphere passes through a cube, or a cube shows its far side through its text.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c depth --see-through",
    )
    see_through: bool = argutils.ArgSpec(
        name="--see-through",
        default=False,
        action="store_true",
        help="Draw one textured cube whose far side shows through the spaces in its text.",
    )  # pyright: ignore[reportAssignmentType]
    "bool : Draw one textured cube whose far side shows through the spaces in its text."


class DepthIterator(BaseEffectIterator[DepthConfig]):
    """Produce the frames of the Depth effect."""

    def __init__(self, effect: Depth) -> None:
        """Set up the bodies and queue their motion."""
        super().__init__(effect)
        self.world = self.terminal.world
        if self.config.see_through:
            cube = self.world.body(Cube(24)).draw(Textured("TTE 3D  ", back="dim"))
            cube.rotate("x", 20)
            cube.spin("y", turns=1, frames=360, ease=easing.in_out_sine)
            self.bodies = (cube,)
        else:
            cube = self.world.body(Cube(20)).draw(Shaded())
            cube.rotate("y", 30).rotate("x", 20)
            # The sphere starts on the left, slightly in front, and passes through the cube to the right.
            start, end = Vec3(-34, 0, 6), Vec3(34, 0, -6)
            sphere = self.world.body(Sphere(9), at=start).draw(Shaded())
            # A path's speed is units per frame, so this one takes 300 frames.
            path = sphere.motion.new_path(speed=(end - start).length() / 300, ease=easing.in_out_sine)
            path.new_waypoint(end)
            sphere.motion.activate_path(path)
            cube.spin("y", turns=0.5, frames=300, ease=easing.in_out_sine)
            self.bodies = (cube, sphere)
        self.text_shown = False

    def __next__(self) -> str:
        """Play the motion, then swap the bodies for the text."""
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


class Depth(BaseEffect[DepthConfig]):
    """A sphere passes through a cube, or a cube shows its far side through its text."""

    @property
    def _config_cls(self) -> type[DepthConfig]:
        return DepthConfig

    @property
    def _iterator_cls(self) -> type[DepthIterator]:
        return DepthIterator
