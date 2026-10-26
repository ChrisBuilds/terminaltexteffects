"""MySpin, tutorial step 1: the text mounted on a flat sheet.

The text starts on a sheet turned away to one side, and the sheet turns back to face the viewer. Later steps build
it up into the Spin effect.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils


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
        """Turn the text plane away and queue the turn back."""
        super().__init__(effect)
        self.world = self.terminal.world
        self.build()

    def build(self) -> None:
        """Show every visible character, turn the text plane away, and queue the turn back."""
        world = self.world
        world.camera.set_perspective(0)
        characters = [character for character in self.terminal.get_characters() if character.input_symbol != " "]
        for character in characters:
            self.terminal.set_character_visibility(character, is_visible=True)
            self.active_characters.add(character)
        # The text plane is the body every character starts on, so turning it turns the text.
        self.sheet = world.text_plane
        self.sheet.rotate("y", 70)
        self.sheet.turn_to_rest(frames=120, ease=easing.out_cubic)

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
