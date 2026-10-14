"""Hop: characters hop to the top of the canvas and back, one column at a time.

An Effect Guide example for the Events chapter. Events chain the two paths, change the character's
symbol at the top, and restore it when the character lands.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import Coord, EffectCharacter, EventHandler, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils

Event = EventHandler.Event
Action = EventHandler.Action


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "hop", Hop, HopConfig


@dataclass
class HopConfig(BaseConfig):
    """Configuration for the Hop effect."""

    parser_spec = argutils.ParserSpec(
        name="hop",
        help="Characters hop to the top of the canvas and back.",
        description="hop | Characters hop to the top of the canvas and back.",
        epilog="Example: tte hop",
    )


class HopIterator(BaseEffectIterator[HopConfig]):
    """Produce the frames of the Hop effect."""

    def __init__(self, effect: Hop) -> None:
        """Give every character a hop, and queue the columns."""
        super().__init__(effect)
        top = self.terminal.canvas.top
        for character in self.terminal.get_characters():
            self.terminal.set_character_visibility(character, is_visible=True)
            rise = character.motion.new_path(speed=0.5, ease=easing.out_quad, hold_time=10, path_id="rise")
            rise.new_waypoint(Coord(character.input_coord.column, top))
            fall = character.motion.new_path(speed=0.5, ease=easing.out_bounce)
            fall.new_waypoint(character.input_coord)

            handler = character.event_handler
            # Rising characters pass in front of the others.
            handler.register_event(Event.PATH_ACTIVATED, rise, Action.SET_LAYER, 1)
            # At the top, show a different symbol while the path holds.
            handler.register_event(
                Event.PATH_HOLDING,
                rise,
                Action.CALLBACK,
                EventHandler.Callback(lambda char: char.animation.set_appearance("*")),
            )
            # When the rise completes, fall back home.
            handler.register_event(Event.PATH_COMPLETE, rise, Action.ACTIVATE_PATH, fall)
            # On landing, restore the input symbol and return to the base layer.
            handler.register_event(Event.PATH_COMPLETE, fall, Action.RESET_APPEARANCE)
            handler.register_event(Event.PATH_COMPLETE, fall, Action.SET_LAYER, 0)
        self.columns: list[list[EffectCharacter]] = self.terminal.get_characters_grouped(order="column_left_to_right")
        self.columns.reverse()
        self.frame_count = 0

    def __next__(self) -> str:
        """Start one column hopping every third frame."""
        if self.columns or self.active_characters:
            if self.columns and self.frame_count % 3 == 0:
                for character in self.columns.pop():
                    character.motion.activate_path("rise")
                    self.active_characters.add(character)
            self.frame_count += 1
            self.update()
            return self.frame
        raise StopIteration


class Hop(BaseEffect[HopConfig]):
    """Characters hop to the top of the canvas and back."""

    @property
    def _config_cls(self) -> type[HopConfig]:
        return HopConfig

    @property
    def _iterator_cls(self) -> type[HopIterator]:
        return HopIterator
