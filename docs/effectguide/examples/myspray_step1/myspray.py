"""MySpray, tutorial step 1: the smallest effect that runs.

The effect shows the input text in place for one frame. Later steps build it up into a copy of the built-in
Spray effect.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "myspray", MySpray, MySprayConfig


@dataclass
class MySprayConfig(BaseConfig):
    """Configuration for the MySpray effect. It has no options yet."""

    parser_spec = argutils.ParserSpec(
        name="myspray",
        help="Sprays the characters from a single point.",
        description="myspray | Sprays the characters from a single point.",
        epilog="Example: tte myspray",
    )


class MySprayIterator(BaseEffectIterator[MySprayConfig]):
    """Produce the frames of the MySpray effect."""

    def __init__(self, effect: MySpray) -> None:
        """Set up every character before the first frame."""
        super().__init__(effect)
        self.shown = False
        for character in self.terminal.get_characters():
            self.terminal.set_character_visibility(character, is_visible=True)

    def __next__(self) -> str:
        """Return one frame showing the text, then stop."""
        if not self.shown:
            self.shown = True
            return self.frame
        raise StopIteration


class MySpray(BaseEffect[MySprayConfig]):
    """Sprays the characters from a single point."""

    @property
    def _config_cls(self) -> type[MySprayConfig]:
        return MySprayConfig

    @property
    def _iterator_cls(self) -> type[MySprayIterator]:
        return MySprayIterator
