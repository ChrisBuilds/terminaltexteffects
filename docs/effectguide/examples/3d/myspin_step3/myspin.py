"""MySpin, tutorial step 3: perspective.

The sheet starts far behind the canvas and spins as it comes forward, growing as it nears. Later steps build it up
into the Spin effect.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.space3d import Body, Space3D
from terminaltexteffects.utils import argutils

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
        """Mount the text on a sheet far behind the canvas and queue its approach."""
        super().__init__(effect)
        self.space = Space3D(self.terminal, perspective=1)
        self.build()

    def build(self) -> None:
        """Mount every visible character on the sheet, move the sheet back, and queue the spin and approach."""
        characters = [character for character in self.terminal.get_characters() if character.input_symbol != " "]
        for character in characters:
            self.terminal.set_character_visibility(character, is_visible=True)
            self.active_characters.add(character)
        self.sheet = self.space.body()
        self.sheet.add_chars(characters, self.sheet.text_plane(characters))
        # The anchors are placed for the sheet's pose at rest, so move the sheet after mounting.
        self.sheet.set_position(0, 0, -START_DISTANCE)
        self.sheet.spin("y", turns=2, frames=SPIN_FRAMES, ease=easing.out_cubic)
        self.sheet.move_to(0, 0, 0, frames=SPIN_FRAMES, ease=easing.out_cubic, together=True)
        self.sheet.on_complete(self.finish)

    def finish(self, sheet: Body) -> None:
        """Hand the characters back, on their input cells."""
        sheet.release_all()

    def __next__(self) -> str:
        """Move the sheet one frame, then the characters with it."""
        if self.space.animating or self.active_characters:
            self.space.step()
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
