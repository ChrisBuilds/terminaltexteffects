"""Handoff: the text tumbles in from far away, settles flat, and then hops as an ordinary 2D effect.

An Effect Guide example for the Animating in 3D chapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import Coord, EffectCharacter, EventHandler, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.tweens import rotation_about
from terminaltexteffects.engine.world import Body
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.geometry3d import Vec3


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "handoff", Handoff, HandoffConfig


@dataclass
class HandoffConfig(BaseConfig):
    """Configuration for the Handoff effect."""

    parser_spec = argutils.ParserSpec(
        name="handoff",
        help="The text tumbles in, settles flat, and then hops as an ordinary 2D effect.",
        description="handoff | The text tumbles in, settles flat, and then hops as an ordinary 2D effect.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c handoff",
    )


class HandoffIterator(BaseEffectIterator[HandoffConfig]):
    """Produce the frames of the Handoff effect."""

    def __init__(self, effect: Handoff) -> None:
        """Push the text plane away, and queue its return."""
        super().__init__(effect)
        self.world = self.terminal.world
        self.plane = self.world.text_plane
        for character in self.plane_characters():
            self.terminal.set_character_visibility(character, is_visible=True)
            self.active_characters.add(character)

        # Jump away at once, then come back with a turn that ends exactly at rest. The return path's speed is
        # units per frame, so it takes 150 frames, as long as the turn.
        self.plane.rotation = rotation_about("x", 60) * rotation_about("y", 200)
        self.plane.position = Vec3(0, 0, -300)
        back = self.plane.motion.new_path(speed=300 / 150, ease=easing.out_cubic)
        back.new_waypoint(Vec3(0, 0, 0))
        self.plane.motion.activate_path(back)
        self.plane.settle("y", turns=1, frames=150, ease=easing.out_cubic)
        self.plane.on_complete(self.hand_off)
        self.columns: list[list[EffectCharacter]] = []
        self.frame_number = 0

    def hand_off(self, plane: Body) -> None:
        """Put the plane back at rest and give every character an ordinary 2D hop from its input cell."""
        plane.reset()
        for character in self.plane_characters():
            up = character.motion.new_path(speed=0.4, ease=easing.out_quad, path_id="up")
            up.new_waypoint(Coord(character.input_coord.column, character.input_coord.row + 2))
            down = character.motion.new_path(speed=0.4, ease=easing.out_bounce, path_id="down")
            down.new_waypoint(character.input_coord)
            handler = character.event_handler
            handler.register_event(EventHandler.Event.PATH_ACTIVATED, up, EventHandler.Action.SET_LAYER, 1)
            handler.register_event(EventHandler.Event.PATH_COMPLETE, up, EventHandler.Action.ACTIVATE_PATH, down)
            handler.register_event(EventHandler.Event.PATH_COMPLETE, down, EventHandler.Action.SET_LAYER, 0)
        self.columns = self.terminal.get_characters_grouped(order="column_left_to_right")
        self.columns.reverse()

    def plane_characters(self) -> list[EffectCharacter]:
        """Return the characters that ride the plane."""
        return [c for c in self.terminal.get_characters() if c.input_symbol != " "]

    def __next__(self) -> str:
        """Play the 3D return, then start the hops one column at a time."""
        if self.world.animating or self.columns or self.active_characters:
            if self.columns and self.frame_number % 2 == 0:
                for character in self.columns.pop():
                    if character.input_symbol != " ":
                        character.motion.activate_path("up")
                        self.active_characters.add(character)
            self.frame_number += 1
            self.update()
            return self.frame
        raise StopIteration


class Handoff(BaseEffect[HandoffConfig]):
    """The text tumbles in, settles flat, and then hops as an ordinary 2D effect."""

    @property
    def _config_cls(self) -> type[HandoffConfig]:
        return HandoffConfig

    @property
    def _iterator_cls(self) -> type[HandoffIterator]:
        return HandoffIterator
