"""Turns: spins about each axis, a tumble, and two ways back to rest.

An Effect Guide example for the Rotation chapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.space3d import Cube, Shaded, Space3D, rotation_about
from terminaltexteffects.utils import argutils


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "turns", Turns, TurnsConfig


@dataclass
class TurnsConfig(BaseConfig):
    """Configuration for the Turns effect."""

    parser_spec = argutils.ParserSpec(
        name="turns",
        help="Spins about each axis, a tumble, and two ways back to rest.",
        description="turns | Spins about each axis, a tumble, and two ways back to rest.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c turns --mode rest",
    )
    mode: str = argutils.ArgSpec(
        name="--mode",
        default="axes",
        choices=["axes", "tumble", "rest"],
        help="axes: one cube spins about each of x, y and z. tumble: two spins run together. rest: two cubes "
        "return to rest from the same pose, one with turn_to_rest and one with settle.",
    )  # pyright: ignore[reportAssignmentType]
    "str : Which turns to show."


class TurnsIterator(BaseEffectIterator[TurnsConfig]):
    """Produce the frames of the Turns effect."""

    def __init__(self, effect: Turns) -> None:
        """Queue the turns for the chosen mode."""
        super().__init__(effect)
        self.space = Space3D(self.terminal)
        if self.config.mode == "axes":
            for axis, x in (("x", -26), ("y", 0), ("z", 26)):
                cube = self.space.body(Cube(14), at=(x, 0, 0)).draw(Shaded())
                cube.hold(30).spin(axis, turns=1, frames=240, ease=easing.in_out_sine).hold(30)
        elif self.config.mode == "tumble":
            cube = self.space.body(Cube(20)).draw(Shaded())
            # Spins queued with together=True run at the same time, and their turns add up into a tumble.
            cube.spin("y", turns=2, frames=360, ease=easing.in_out_sine)
            cube.spin("x", turns=1, frames=360, ease=easing.in_out_sine, together=True)
        else:
            pose = rotation_about("diagonal", 140) * rotation_about("y", 60)
            for x in (-20, 20):
                cube = self.space.body(Cube(16), at=(x, 0, 0)).draw(Shaded())
                cube.set_rotation(pose)
                cube.hold(45)
            left, right = self.space.bodies
            left.turn_to_rest(frames=150, ease=easing.in_out_cubic).hold(45)
            right.settle("y", turns=1, frames=150, ease=easing.in_out_cubic).hold(45)
        self.text_shown = False

    def __next__(self) -> str:
        """Play the turns, then swap the cubes for the text."""
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


class Turns(BaseEffect[TurnsConfig]):
    """Spins about each axis, a tumble, and two ways back to rest."""

    @property
    def _config_cls(self) -> type[TurnsConfig]:
        return TurnsConfig

    @property
    def _iterator_cls(self) -> type[TurnsIterator]:
        return TurnsIterator
