"""Reveal: show the characters one group per frame, in a chosen order.

An Effect Guide example for the Characters chapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import CharacterOrder, EffectCharacter
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "reveal", Reveal, RevealConfig


@dataclass
class RevealConfig(BaseConfig):
    """Configuration for the Reveal effect."""

    parser_spec = argutils.ParserSpec(
        name="reveal",
        help="Reveals the characters one group per frame.",
        description="reveal | Reveals the characters one group per frame.",
        epilog="Example: tte reveal --order spiral_clockwise",
    )
    order: CharacterOrder = argutils.ArgSpec(
        name="--order",
        type=argutils.CharacterOrderArg.type_parser,
        default=CharacterOrder.ROW_TOP_TO_BOTTOM,
        metavar=" ".join(argutils.CharacterOrderArg.METAVAR),
        help="Order in which to reveal the characters.",
    )  # pyright: ignore[reportAssignmentType]
    "CharacterOrder : Order in which to reveal the characters."


class RevealIterator(BaseEffectIterator[RevealConfig]):
    """Produce the frames of the Reveal effect."""

    def __init__(self, effect: Reveal) -> None:
        """Group the characters in the configured order."""
        super().__init__(effect)
        self.groups: list[list[EffectCharacter]] = self.terminal.get_characters_grouped(order=self.config.order)
        self.groups.reverse()  # Pop groups from the end, in reveal order.

    def __next__(self) -> str:
        """Show the next group, until every group is shown."""
        if self.groups:
            for character in self.groups.pop():
                self.terminal.set_character_visibility(character, is_visible=True)
            return self.frame
        raise StopIteration


class Reveal(BaseEffect[RevealConfig]):
    """Reveals the characters one group per frame."""

    @property
    def _config_cls(self) -> type[RevealConfig]:
        return RevealConfig

    @property
    def _iterator_cls(self) -> type[RevealIterator]:
        return RevealIterator
