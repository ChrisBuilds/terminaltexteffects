"""Spawns characters jumbled, explodes them to the edge of the canvas, then reassembles them.

Classes:
    Unstable: Spawns characters jumbled, explodes them to the edge of the canvas, then reassembles them.
    UnstableConfig: Configuration for the Unstable effect.
    UnstableIterator: Effect iterator for the Unstable effect. Does not normally need to be called directly.
"""

from __future__ import annotations

import random
import typing
from dataclasses import dataclass

from terminaltexteffects import Color, Coord, EffectCharacter, Gradient, easing
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argvalidators
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    """Get the effect class and its configuration class."""
    return Unstable, UnstableConfig


@argclass(
    name="unstable",
    help="Spawn characters jumbled, explode them to the edge of the canvas, then reassemble them in the "
    "correct layout.",
    description="unstable | Spawn characters jumbled, explode them to the edge of the canvas, then reassemble them "
    "in the correct layout.",
    epilog=(
        f"{argvalidators.EASING_EPILOG} Example: terminaltexteffects unstable --unstable-color ff9200 "
        "--final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --explosion-ease OUT_EXPO "
        "--explosion-speed 0.75 --reassembly-ease OUT_EXPO --reassembly-speed 0.75"
    ),
)
@dataclass
class UnstableConfig(ArgsDataClass):
    """Configuration for the Unstable effect.

    Attributes:
        unstable_color (Color): Color transitioned to as the characters become unstable.
        explosion_ease (easing.EasingFunction): Easing function to use for character movement during the explosion.
        explosion_speed (float): Speed of characters during explosion. Valid values are n > 0.
        reassembly_ease (easing.EasingFunction): Easing function to use for character reassembly.
        reassembly_speed (float): Speed of characters during reassembly. Valid values are n > 0.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one color is
            provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps will
            create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.

    """

    unstable_color: Color = ArgField(
        cmd_name=["--unstable-color"],
        type_parser=argvalidators.ColorArg.type_parser,
        default=Color("ff9200"),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Color transitioned to as the characters become unstable.",
    )  # type: ignore[assignment]
    "Color : Color transitioned to as the characters become unstable."

    explosion_ease: easing.EasingFunction = ArgField(
        cmd_name=["--explosion-ease"],
        type_parser=argvalidators.Ease.type_parser,
        default=easing.out_expo,
        help="Easing function to use for character movement during the explosion.",
    )  # type: ignore[assignment]
    "easing.EasingFunction : Easing function to use for character movement during the explosion."

    explosion_speed: float = ArgField(
        cmd_name=["--explosion-speed"],
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=0.75,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Speed of characters during explosion. ",
    )  # type: ignore[assignment]
    "float : Speed of characters during explosion. "

    reassembly_ease: easing.EasingFunction = ArgField(
        cmd_name=["--reassembly-ease"],
        type_parser=argvalidators.Ease.type_parser,
        default=easing.out_expo,
        help="Easing function to use for character reassembly.",
    )  # type: ignore[assignment]
    "easing.EasingFunction : Easing function to use for character reassembly."

    reassembly_speed: float = ArgField(
        cmd_name=["--reassembly-speed"],
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=0.75,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Speed of characters during reassembly. ",
    )  # type: ignore[assignment]
    "float : Speed of characters during reassembly."

    final_gradient_stops: tuple[Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("8A008A"), Color("00D1FF"), Color("FFFFFF")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied across the canvas). If "
        "only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    (
        "tuple[Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the "
        "characters will be displayed in that color."
    )

    final_gradient_steps: tuple[int, ...] | int = ArgField(
        cmd_name=["--final-gradient-steps"],
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a "
        "smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    (
        "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. More steps will "
        "create a smoother and longer gradient animation."
    )

    final_gradient_direction: Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=Gradient.Direction.VERTICAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "Gradient.Direction : Direction of the final gradient."

    @classmethod
    def get_effect_class(cls) -> type[Unstable]:
        """Get the effect class associated with this configuration."""
        return Unstable


class UnstableIterator(BaseEffectIterator[UnstableConfig]):
    """Effect iterator for the Unstable effect."""

    def __init__(self, effect: Unstable) -> None:
        """Initialize the effect iterator."""
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.jumbled_coords: dict[EffectCharacter, Coord] = {}
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.build()

    def build(self) -> None:
        """Build the initial effect state."""
        final_gradient = Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.text_bottom,
            self.terminal.canvas.text_top,
            self.terminal.canvas.text_left,
            self.terminal.canvas.text_right,
            self.config.final_gradient_direction,
        )
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
        character_coords = [character.input_coord for character in self.terminal.get_characters()]
        for character in self.terminal.get_characters():
            pos = random.randint(0, 3)
            if pos == 0:
                col = self.terminal.canvas.left
                row = self.terminal.canvas.random_row()
            elif pos == 1:
                col = self.terminal.canvas.right
                row = self.terminal.canvas.random_row()
            elif pos == 2:
                col = self.terminal.canvas.random_column()
                row = self.terminal.canvas.bottom
            else:
                col = self.terminal.canvas.random_column()
                row = self.terminal.canvas.top
            jumbled_coord = character_coords.pop(random.randint(0, len(character_coords) - 1))
            self.jumbled_coords[character] = jumbled_coord
            character.motion.set_coordinate(jumbled_coord)
            explosion_path = character.motion.new_path(path_id="explosion", speed=1.25, ease=self.config.explosion_ease)
            explosion_path.new_waypoint(Coord(col, row))
            reassembly_path = character.motion.new_path(
                path_id="reassembly",
                speed=0.75,
                ease=self.config.reassembly_ease,
            )
            reassembly_path.new_waypoint(character.input_coord)
            unstable_gradient = Gradient(
                self.character_final_color_map[character],
                self.config.unstable_color,
                steps=25,
            )
            rumble_scn = character.animation.new_scene(scene_id="rumble")
            rumble_scn.apply_gradient_to_symbols(character.input_symbol, 10, fg_gradient=unstable_gradient)
            final_color = Gradient(self.config.unstable_color, self.character_final_color_map[character], steps=12)
            final_scn = character.animation.new_scene(scene_id="final")
            final_scn.apply_gradient_to_symbols(character.input_symbol, 5, fg_gradient=final_color)
            character.animation.activate_scene(rumble_scn)
            self.terminal.set_character_visibility(character, is_visible=True)
        self._explosion_hold_time = 50
        self.phase = "rumble"
        self._max_rumble_steps = 250
        self._current_rumble_steps = 0
        self._rumble_mod_delay = 20

    def __next__(self) -> str:
        """Return the next from in the effect."""
        next_frame = None
        if self.phase == "rumble":
            if self._current_rumble_steps < self._max_rumble_steps:
                if self._current_rumble_steps > 30 and self._current_rumble_steps % self._rumble_mod_delay == 0:
                    row_offset = random.choice([-1, 0, 1])
                    column_offset = random.choice([-1, 0, 1])
                    for character in self.terminal.get_characters():
                        character.motion.set_coordinate(
                            Coord(
                                character.motion.current_coord.column + column_offset,
                                character.motion.current_coord.row + row_offset,
                            ),
                        )
                        character.animation.step_animation()
                    next_frame = self.frame
                    for character in self.terminal.get_characters():
                        character.motion.set_coordinate(self.jumbled_coords[character])
                    self._rumble_mod_delay -= 1
                    self._rumble_mod_delay = max(self._rumble_mod_delay, 1)
                else:
                    for character in self.terminal.get_characters():
                        character.animation.step_animation()
                    next_frame = self.frame

                self._current_rumble_steps += 1
            else:
                self.phase = "explosion"
                for character in self.terminal.get_characters():
                    character.motion.activate_path(character.motion.query_path("explosion"))
                self.active_characters = set(self.terminal.get_characters())

        if self.phase == "explosion":
            if self.active_characters:
                for character in self.active_characters:
                    character.tick()
                self.active_characters = {
                    character
                    for character in self.active_characters
                    if character.motion.current_coord != character.motion.query_path("explosion").waypoints[0].coord
                }
                next_frame = self.frame

            elif self._explosion_hold_time:
                for character in self.active_characters:
                    character.tick()
                self._explosion_hold_time -= 1
                next_frame = self.frame
            else:
                self.phase = "reassembly"
                for character in self.terminal.get_characters():
                    character.animation.activate_scene(character.animation.query_scene("final"))
                    self.active_characters.add(character)
                    character.motion.activate_path(character.motion.query_path("reassembly"))

        if self.phase == "reassembly" and self.active_characters:
            for character in self.active_characters:
                character.tick()
            self.active_characters = {
                character
                for character in self.active_characters
                if character.motion.current_coord != character.motion.query_path("reassembly").waypoints[0].coord
                or not character.animation.active_scene_is_complete()
            }
            next_frame = self.frame

        if next_frame is not None:
            return next_frame
        raise StopIteration


class Unstable(BaseEffect[UnstableConfig]):
    """Spawns characters jumbled, explodes them to the edge of the canvas, then reassembles them.

    Attributes:
        effect_config (UnstableConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    @property
    def _config_cls(self) -> type[UnstableConfig]:
        return UnstableConfig

    @property
    def _iterator_cls(self) -> type[UnstableIterator]:
        return UnstableIterator
