"""Orbit: a planet turns in place while a moon orbits it.

An Effect Guide example for the Transforms chapter. Both bodies turn by the same angle each frame. The planet
turns about its own center. The moon's position is turned about the world origin, so it travels around the planet.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.drawing import Shaded
from terminaltexteffects.engine.shapes import Cube
from terminaltexteffects.engine.tweens import rotation_about
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.geometry3d import Vec3


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "orbit", Orbit, OrbitConfig


@dataclass
class OrbitConfig(BaseConfig):
    """Configuration for the Orbit effect."""

    parser_spec = argutils.ParserSpec(
        name="orbit",
        help="A planet turns in place while a moon orbits it.",
        description="orbit | A planet turns in place while a moon orbits it.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c orbit",
    )
    frames: int = argutils.ArgSpec(
        name="--frames",
        type=argutils.PositiveInt.type_parser,
        default=360,
        metavar=argutils.PositiveInt.METAVAR,
        help="Frames for one full orbit.",
    )  # pyright: ignore[reportAssignmentType]
    "int : Frames for one full orbit."


class OrbitIterator(BaseEffectIterator[OrbitConfig]):
    """Produce the frames of the Orbit effect."""

    def __init__(self, effect: Orbit) -> None:
        """Place the planet at the origin and the moon to its right."""
        super().__init__(effect)
        self.world = self.terminal.world
        self.planet = self.world.body(Cube(16)).draw(Shaded())
        self.moon = self.world.body(Cube(6)).draw(Shaded())
        self.moon_start = Vec3(30, 0, 0)  # Where the moon starts, relative to the origin.
        self.tilt = rotation_about("x", 20)  # Tip the top toward the viewer, so we look down on the orbit.
        self.frame_number = 0
        self.text_shown = False

    def __next__(self) -> str:
        """Turn both bodies one step, then swap them for the text after one orbit."""
        if self.frame_number <= self.config.frames:
            turn = rotation_about("y", 360 * self.frame_number / self.config.frames)
            # Spin in place: only the planet's orientation changes. Its position stays at the origin.
            self.planet.rotation = self.tilt * turn
            # Orbit: the moon's position is turned about the origin, then the moon is moved there.
            self.moon.rotation = self.tilt * turn
            self.moon.position = (self.tilt * turn).apply(self.moon_start)
            self.frame_number += 1
        elif not self.text_shown:
            for body in (self.planet, self.moon):
                body.erase()  # The world hides its cells when it next paints.
            for character in self.terminal.get_characters():
                self.terminal.set_character_visibility(character, is_visible=True)
            self.text_shown = True
        else:
            raise StopIteration
        self.update()
        return self.frame


class Orbit(BaseEffect[OrbitConfig]):
    """A planet turns in place while a moon orbits it."""

    @property
    def _config_cls(self) -> type[OrbitConfig]:
        return OrbitConfig

    @property
    def _iterator_cls(self) -> type[OrbitIterator]:
        return OrbitIterator
