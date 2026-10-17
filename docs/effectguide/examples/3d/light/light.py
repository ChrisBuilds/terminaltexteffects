"""Light: the light circles a slowly turning shape.

An Effect Guide example for the Light and Shading chapter.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from terminaltexteffects import Color, ColorPair
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.space3d import Shaded, Space3D, Sphere, Torus
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.geometry3d import Vec3


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "light", Light, LightConfig


@dataclass
class LightConfig(BaseConfig):
    """Configuration for the Light effect."""

    parser_spec = argutils.ParserSpec(
        name="light",
        help="The light circles a slowly turning shape.",
        description="light | The light circles a slowly turning shape.",
        epilog='Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c light --symbols " .:-=+*#%@"',
    )
    shape: str = argutils.ArgSpec(
        name="--shape",
        default="sphere",
        choices=["sphere", "torus"],
        help="The shape to light.",
    )  # pyright: ignore[reportAssignmentType]
    "str : The shape to light."

    symbols: str = argutils.ArgSpec(
        name="--symbols",
        default=".,-~:;=!*#$@",
        help="Shading symbols from unlit to fully lit.",
    )  # pyright: ignore[reportAssignmentType]
    "str : Shading symbols from unlit to fully lit."


class LightIterator(BaseEffectIterator[LightConfig]):
    """Produce the frames of the Light effect."""

    def __init__(self, effect: Light) -> None:
        """Draw the shape with the chosen symbols."""
        super().__init__(effect)
        self.space = Space3D(self.terminal)
        shape = Sphere(radius=16, segments=32, rings=16) if self.config.shape == "sphere" else Torus(18, 7)
        self.body = self.space.body(shape).draw(Shaded(symbols=self.config.symbols))
        self.body.rotate("x", 30)
        # A sun marks where the light is. It is mounted on a body of its own, so the space places it in 3D and the
        # shape hides it while the light is behind.
        self.sun = self.space.body()
        self.sun_character = self.terminal.add_character("☼", self.terminal.canvas.center)
        self.sun_character.animation.set_appearance("☼", ColorPair(fg=Color("#ffd75f")))
        self.sun.add_char(self.sun_character, self.sun.anchor(0, 0, 0))
        self.terminal.set_character_visibility(self.sun_character, is_visible=True)
        self.active_characters.add(self.sun_character)
        self.frames = 360
        self.frame_number = 0
        self.text_shown = False

    def __next__(self) -> str:
        """Move the light one step around the shape, then swap the shape for the text."""
        if self.frame_number < self.frames:
            # The light travels a full circle around the y axis, a little above the shape and in front of it at
            # the start. Space3D.light is the direction toward the light, so it must be a unit vector.
            angle = 2 * math.pi * self.frame_number / self.frames
            self.space.light = Vec3(math.sin(angle), 0.5, math.cos(angle)).normalized()
            light = self.space.light
            self.sun.set_position(light.x * 26, light.y * 26, light.z * 26)
            self.body.rotate("y", 0.5)
            self.space.step()
            self.frame_number += 1
        elif not self.text_shown:
            self.body.erase()
            self.sun.release_all()
            self.terminal.set_character_visibility(self.sun_character, is_visible=False)
            self.space.step()  # Hides the surface characters once nothing is drawn.
            for character in self.terminal.get_characters():
                self.terminal.set_character_visibility(character, is_visible=True)
            self.text_shown = True
        else:
            raise StopIteration
        self.update()
        return self.frame


class Light(BaseEffect[LightConfig]):
    """The light circles a slowly turning shape."""

    @property
    def _config_cls(self) -> type[LightConfig]:
        return LightConfig

    @property
    def _iterator_cls(self) -> type[LightIterator]:
        return LightIterator
