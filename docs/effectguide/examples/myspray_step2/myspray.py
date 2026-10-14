"""MySpray, tutorial step 2: release the characters a few at a time.

Characters appear in a random order, one or more per frame, until the whole text is shown.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from terminaltexteffects import EffectCharacter
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
        self.pending_chars: list[EffectCharacter] = []
        self.build()

    def build(self) -> None:
        """Queue every character for release in a random order."""
        self.pending_chars.extend(self.terminal.get_characters())
        random.shuffle(self.pending_chars)
        # Release up to 0.5% of the characters per frame, and at least one.
        self._volume = max(int(len(self.pending_chars) * 0.005), 1)

    def __next__(self) -> str:
        """Release a few characters, advance the animation, and return the frame."""
        if self.pending_chars or self.active_characters:
            for _ in range(random.randint(1, self._volume)):
                if self.pending_chars:
                    next_character = self.pending_chars.pop()
                    self.terminal.set_character_visibility(next_character, is_visible=True)
                    self.active_characters.add(next_character)
            self.update()
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
