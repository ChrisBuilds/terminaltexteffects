"""Card: the input text turns like a card, showing how characters on a turning body thin out edge-on.

An Effect Guide example for the Depth and Hidden Surfaces chapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "card", Card, CardConfig


@dataclass
class CardConfig(BaseConfig):
    """Configuration for the Card effect."""

    parser_spec = argutils.ParserSpec(
        name="card",
        help="The input text turns like a card.",
        description="card | The input text turns like a card.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c card --hide-back",
    )
    hide_back: bool = argutils.ArgSpec(
        name="--hide-back",
        default=False,
        action="store_true",
        help="Hide characters while the back of the card faces the viewer.",
    )  # pyright: ignore[reportAssignmentType]
    "bool : Hide characters while the back of the card faces the viewer."


class CardIterator(BaseEffectIterator[CardConfig]):
    """Produce the frames of the Card effect."""

    def __init__(self, effect: Card) -> None:
        """Turn the text plane itself, the body every character starts on, once and slowly."""
        super().__init__(effect)
        self.world = self.terminal.world
        card = self.world.text_plane
        card.hide_facing_away = self.config.hide_back
        for character in self.terminal.get_characters():
            if character.input_symbol != " ":
                self.terminal.set_character_visibility(character, is_visible=True)
        card.hold(20).spin("y", turns=1, frames=360, ease=easing.in_out_sine).hold(20)

    def __next__(self) -> str:
        """Turn the card until it is back at rest."""
        if self.world.animating:
            self.update()
            return self.frame
        raise StopIteration


class Card(BaseEffect[CardConfig]):
    """The input text turns like a card."""

    @property
    def _config_cls(self) -> type[CardConfig]:
        return CardConfig

    @property
    def _iterator_cls(self) -> type[CardIterator]:
        return CardIterator
