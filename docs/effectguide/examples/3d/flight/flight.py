"""Flight: the text flies onto a spinning cube, rides it for a while, and then flies home.

An Effect Guide example for the Attaching and Detaching chapter.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from terminaltexteffects import EffectCharacter, EventHandler, Shaded, Vec3, easing, rotation_about
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.shapes import Cube
from terminaltexteffects.utils import argutils


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "flight", Flight, FlightConfig


@dataclass
class FlightConfig(BaseConfig):
    """Configuration for the Flight effect."""

    ride_frames: int = argutils.ArgSpec(
        name="--ride-frames",
        type=argutils.PositiveInt.type_parser,
        default=120,
        metavar=argutils.PositiveInt.METAVAR,
        help="Frames the text rides the cube once every character has landed.",
    )  # pyright: ignore[reportAssignmentType]
    "int : Frames the text rides the cube once every character has landed."

    parser_spec = argutils.ParserSpec(
        name="flight",
        help="The text flies onto a spinning cube, rides it, and flies home.",
        description="flight | The text flies onto a spinning cube, rides it, and flies home.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c flight --ride-frames 120",
    )


class FlightIterator(BaseEffectIterator[FlightConfig]):
    """Produce the frames of the Flight effect."""

    def __init__(self, effect: Flight) -> None:
        """Build the cube and give every character a flight to a live target on it."""
        super().__init__(effect)
        self.world = self.terminal.world
        self.world.set_light("upper left")
        self.cube = self.world.body(Cube(24), at=(0, 0, -30)).draw(Shaded())
        self.cube.rotation = rotation_about("x", 20)
        self.cube.spin("y", turns=6, frames=1200, local=True)

        self.waiting: list[EffectCharacter] = []
        for character in self.terminal.get_characters():
            if character.input_symbol == " ":
                continue
            self.terminal.set_character_visibility(character, is_visible=True)
            # A target is a spot on the cube's surface that moves with the cube. The path reads where it is every
            # tick, so the character lands on the spot however far the cube has turned meanwhile.
            target = self.cube.surface.target(self.cube.surface.random_coord())
            flight = character.motion.new_path(speed=1.2, ease=easing.in_out_sine, path_id="flight")
            # The control point is on the text plane, 30 units toward the viewer, so the character rises off it first.
            column, row = character.input_coord.column, character.input_coord.row
            flight.new_waypoint(target, bezier_control=Vec3(column, row, 30))
            # On landing, become the cube's child where it is: from then on the character turns with the cube.
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE, flight, EventHandler.Action.ATTACH, self.cube
            )
            self.waiting.append(character)
        random.shuffle(self.waiting)
        self.total = len(self.waiting)
        self.ride = self.config.ride_frames
        self.going_home = False

    def go_home(self) -> None:
        """Move every character back onto the text plane where it is, and fly it to its input cell."""
        for character in self.terminal.get_characters():
            if character.input_symbol == " ":
                continue
            # attach() without `at` keeps the character's place in the world, so it doesn't jump. Its position is
            # now on the text plane, and a path there can head for its input cell.
            character.attach(self.world.text_plane)
            home = character.motion.new_path(speed=1.0, ease=easing.in_out_cubic, path_id="home")
            home.new_waypoint(character.input_coord)
            character.motion.activate_path(home)
            self.active_characters.add(character)
        self.cube.cancel()
        self.cube.scale_to(0.05, frames=60, ease=easing.in_back)
        self.going_home = True

    def __next__(self) -> str:
        """Launch a few characters a frame, ride, then send everything home and end once it's there."""
        for _ in range(4):
            if self.waiting:
                character = self.waiting.pop()
                character.motion.activate_path("flight")
                self.active_characters.add(character)
        if not self.waiting and not self.going_home and len(self.cube.children) == self.total:
            self.ride -= 1
            if self.ride <= 0:
                self.go_home()
        if self.going_home and not self.active_characters and not self.world.animating:
            if self.cube in self.world.bodies:
                self.world.remove(self.cube)
            else:
                raise StopIteration
        self.update()
        return self.frame


class Flight(BaseEffect[FlightConfig]):
    """The text flies onto a spinning cube, rides it, and flies home."""

    @property
    def _config_cls(self) -> type[FlightConfig]:
        return FlightConfig

    @property
    def _iterator_cls(self) -> type[FlightIterator]:
        return FlightIterator
