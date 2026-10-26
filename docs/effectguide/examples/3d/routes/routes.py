"""Routes: the text walks around a box, climbs onto its lid, takes the shortest way back, and flies home.

An Effect Guide example for the Surfaces chapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import EffectCharacter, EventHandler, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.drawing import Shaded
from terminaltexteffects.engine.shapes import Box
from terminaltexteffects.engine.tweens import rotation_about
from terminaltexteffects.utils import argutils


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "routes", Routes, RoutesConfig


@dataclass
class RoutesConfig(BaseConfig):
    """Configuration for the Routes effect."""

    parser_spec = argutils.ParserSpec(
        name="routes",
        help="The text walks around a box, climbs onto its lid, and takes the shortest way back.",
        description="routes | The text walks around a box, climbs onto its lid, and takes the shortest way back.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c routes",
    )


class RoutesIterator(BaseEffectIterator[RoutesConfig]):
    """Produce the frames of the Routes effect."""

    def __init__(self, effect: Routes) -> None:
        """Lay the text out on the box's front, and chain four moves over its surface."""
        super().__init__(effect)
        self.world = self.terminal.world
        self.world.set_light("upper left")
        self.box = self.world.body(Box(50, 20, 24), at=(0, -6, 10)).draw(Shaded())
        self.box.rotation = rotation_about("y", -20) * rotation_about("x", 30)

        characters = [c for c in self.terminal.get_characters() if c.input_symbol != " "]
        # Attach the text to the box's front face, laid out as the input reads.
        self.box.surface.face("front").layout_text(characters)
        for character in characters:
            self.terminal.set_character_visibility(character, is_visible=True)
            home = character.motion.position  # (column, row, height) on the box's surface.
            moves = character.motion
            # walk() goes straight ahead by an amount, over every edge it meets.
            around = moves.new_path(speed=0.5, ease=easing.in_out_sine, path_id="around")
            around.walk(columns=50)
            back = moves.new_path(speed=0.5, ease=easing.in_out_sine, path_id="back")
            back.walk(columns=-50)
            over = moves.new_path(speed=0.3, ease=easing.in_out_sine, path_id="over")
            over.walk(rows=12)
            # A waypoint on a closed surface is reached by the shortest straight route, over the edges between.
            return_path = moves.new_path(speed=0.3, ease=easing.in_out_sine, path_id="return")
            return_path.new_waypoint(home)
            handler = character.event_handler
            for finished, following in ((around, back), (back, over), (over, return_path)):
                handler.register_event(
                    EventHandler.Event.PATH_COMPLETE, finished, EventHandler.Action.ACTIVATE_PATH, following
                )
        self.characters: list[EffectCharacter] = characters
        self.delay = 40
        self.going_home = False

    def go_home(self) -> None:
        """Hand the text back: onto the text plane where it is, then along a path to its input cell."""
        for character in self.characters:
            character.attach(self.world.text_plane)
            home = character.motion.new_path(speed=0.8, ease=easing.in_out_cubic, path_id="home")
            home.new_waypoint(character.input_coord)
            character.motion.activate_path(home)
            self.active_characters.add(character)
        self.box.scale_to(0.05, frames=40, ease=easing.in_back)
        self.going_home = True

    def __next__(self) -> str:
        """Hold the text on the front for a moment, walk it until every move is done, then send it home."""
        if self.delay:
            self.delay -= 1
            if not self.delay:
                for character in self.characters:
                    character.motion.activate_path("around")
                    self.active_characters.add(character)
        elif not self.active_characters and not self.world.animating:
            if not self.going_home:
                self.go_home()
            elif self.box in self.world.bodies:
                self.world.remove(self.box)
            else:
                raise StopIteration
        self.update()
        return self.frame


class Routes(BaseEffect[RoutesConfig]):
    """The text walks around a box, climbs onto its lid, and takes the shortest way back."""

    @property
    def _config_cls(self) -> type[RoutesConfig]:
        return RoutesConfig

    @property
    def _iterator_cls(self) -> type[RoutesIterator]:
        return RoutesIterator
