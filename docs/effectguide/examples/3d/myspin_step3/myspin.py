"""MySpin, tutorial step 3: perspective.

The sheet starts far behind the canvas and spins as it comes forward, growing as it nears. Later steps build it up
into the Spin effect.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.geometry3d import Vec3

START_DISTANCE = 200
"""How far behind the canvas the sheet starts, in columns."""

SPIN_FRAMES = 240
"""Frames from the start until the sheet lands."""


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "myspin", MySpin, MySpinConfig


@dataclass
class MySpinConfig(BaseConfig):
    """Configuration for the MySpin effect. It has no options yet."""

    parser_spec = argutils.ParserSpec(
        name="myspin",
        help="The text tumbles in from the distance as a flat sheet, spins, and settles into place.",
        description="myspin | The text tumbles in from the distance as a flat sheet, spins, and settles into place.",
        epilog="Example: tte myspin",
    )


class MySpinIterator(BaseEffectIterator[MySpinConfig]):
    """Produce the frames of the MySpin effect."""

    def __init__(self, effect: MySpin) -> None:
        """Move the text plane far behind the canvas and queue its approach."""
        super().__init__(effect)
        self.world = self.terminal.world
        self.build()

    def build(self) -> None:
        """Show every visible character, move the text plane back, and queue the spin and approach."""
        world = self.world
        world.camera.set_perspective(1)
        characters = [character for character in self.terminal.get_characters() if character.input_symbol != " "]
        for character in characters:
            self.terminal.set_character_visibility(character, is_visible=True)
            self.active_characters.add(character)
        self.sheet = world.text_plane
        self.sheet.position = Vec3(0, 0, -START_DISTANCE)
        self.sheet.spin("y", turns=2, frames=SPIN_FRAMES, ease=easing.out_cubic)
        # A body moves along paths like a character: here straight back to the canvas, in step with the spin.
        approach = self.sheet.motion.new_path(speed=START_DISTANCE / SPIN_FRAMES, ease=easing.out_cubic)
        approach.new_waypoint(Vec3(0, 0, 0))
        self.sheet.motion.activate_path(approach)

    def __next__(self) -> str:
        """Move the text plane one frame; the characters on it move with it."""
        if self.world.animating or self.active_characters:
            self.update()
            return self.frame
        raise StopIteration


class MySpin(BaseEffect[MySpinConfig]):
    """The text tumbles in from the distance as a flat sheet, spins, and settles into place."""

    @property
    def _config_cls(self) -> type[MySpinConfig]:
        return MySpinConfig

    @property
    def _iterator_cls(self) -> type[MySpinIterator]:
        return MySpinIterator
