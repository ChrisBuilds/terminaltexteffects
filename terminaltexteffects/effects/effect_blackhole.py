"""Creates a blackhole in a starfield, consumes the stars, explodes the input data back into position.

Classes:
    BlackholeConfig: Configuration for the Blackhole effect.
    Blackhole: Creates a blackhole in a starfield, consumes the stars, explodes the input data back into position.
    BlackholeIterator: Iterator for the Blackhole effect. Does not normally need to be called directly.

"""

from __future__ import annotations

import random
import typing
from dataclasses import dataclass

from terminaltexteffects import Color, Coord, EffectCharacter, EventHandler, Gradient, Scene, easing, geometry
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argvalidators
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.graphics import ColorPair


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    """Return the Blackhole effect class and its configuration class."""
    return Blackhole, BlackholeConfig


@argclass(
    name="blackhole",
    help="Characters are consumed by a black hole and explode outwards.",
    description="blackhole | Characters are consumed by a black hole and explode outwards.",
    epilog="Example: terminaltexteffects blackhole --star-colors ffcc0d ff7326 ff194d bf2669 702a8c 049dbf "
    "--final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --final-gradient-direction vertical",
)
@dataclass
class BlackholeConfig(ArgsDataClass):
    """Configuration for the Blackhole effect.

    Attributes:
        blackhole_color (Color): Color for the stars that comprise the blackhole border.
        star_colors (tuple[Color, ...]): Tuple of colors from which character colors will be chosen and applied
            after the explosion, but before the cooldown to final color.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the character gradient. If only one color is
            provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps will
            create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.

    """

    blackhole_color: Color = ArgField(
        cmd_name=["--blackhole-color"],
        type_parser=argvalidators.ColorArg.type_parser,
        default=Color("ffffff"),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Color for the stars that comprise the blackhole border.",
    )  # type: ignore[assignment]

    "Color : Color for the stars that comprise the blackhole border."

    star_colors: tuple[Color, ...] = ArgField(
        cmd_name=["--star-colors"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("ffcc0d"), Color("ff7326"), Color("ff194d"), Color("bf2669"), Color("702a8c"), Color("049dbf")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="List of colors from which character colors will be chosen and applied after the explosion, but before "
        "the cooldown to final color.",
    )  # type: ignore[assignment]

    (
        "tuple[Color, ...] : Tuple of colors from which character colors will be chosen and applied after the "
        "explosion, but before the cooldown to final color."
    )

    final_gradient_stops: tuple[Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("8A008A"), Color("00D1FF"), Color("ffffff")),
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
        "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. More steps will create "
        "a smoother and longer gradient animation."
    )

    final_gradient_direction: Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=Gradient.Direction.DIAGONAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]

    "Gradient.Direction : Direction of the final gradient."

    @classmethod
    def get_effect_class(cls) -> type[Blackhole]:
        """Return the effect class associated with this configuration."""
        return Blackhole


class BlackholeIterator(BaseEffectIterator[BlackholeConfig]):
    """Iterator for the Blackhole effect."""

    def __init__(self, effect: Blackhole) -> None:
        """Initialize the Blackhole effect iterator.

        Args:
            effect (Blackhole): The Blackhole effect instance.

        """
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.blackhole_chars: list[EffectCharacter] = []
        self.awaiting_consumption_chars: list[EffectCharacter] = []
        self.blackhole_radius = max(
            min(
                round(self.terminal.canvas.width * 0.3),
                round(self.terminal.canvas.height * 0.3),
            ),
            3,
        )
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.preexisting_colors_present = any(
            any((character.animation.input_fg_color, character.animation.input_bg_color))
            for character in self.terminal.get_characters()
        )
        self.build()

    def prepare_blackhole(self) -> None:
        """Prepare the blackhole and starfield characters."""
        star_symbols = ["*", "'", "`", "¤", "•", "°", "·"]
        starfield_colors = Gradient(Color("4a4a4d"), Color("ffffff"), steps=6).spectrum
        gradient_map = {}
        for color in starfield_colors:
            gradient_map[color] = Gradient(color, Color("000000"), steps=10)
        available_chars = list(self.terminal._input_characters)
        while len(self.blackhole_chars) < self.blackhole_radius * 3 and available_chars:
            self.blackhole_chars.append(available_chars.pop(random.randrange(0, len(available_chars))))
        black_hole_ring_positions = geometry.find_coords_on_circle(
            self.terminal.canvas.center,
            self.blackhole_radius,
            len(self.blackhole_chars),
        )
        for position_index, character in enumerate(self.blackhole_chars):
            starting_pos = black_hole_ring_positions[position_index]
            blackhole_path = character.motion.new_path(path_id="blackhole", speed=0.5, ease=easing.in_out_sine)
            blackhole_path.new_waypoint(starting_pos)
            blackhole_scn = character.animation.new_scene(scene_id="blackhole")
            blackhole_scn.add_frame("*", 1, colors=ColorPair(fg=self.config.blackhole_color))
            character.event_handler.register_event(
                EventHandler.Event.PATH_ACTIVATED,
                blackhole_path,
                EventHandler.Action.SET_LAYER,
                1,
            )
            # make rotation waypoints
            blackhole_rotation_path = character.motion.new_path(path_id="blackhole_rotation", speed=0.2, loop=True)
            for coord in black_hole_ring_positions[position_index:] + black_hole_ring_positions[:position_index]:
                blackhole_rotation_path.new_waypoint(coord, waypoint_id=str(len(blackhole_rotation_path.waypoints)))
        for character in self.terminal.get_characters():
            self.terminal.set_character_visibility(character, is_visible=True)
            starting_scn = character.animation.new_scene()
            star_symbol = random.choice(star_symbols)
            star_color = random.choice(starfield_colors)
            starting_scn.add_frame(star_symbol, 1, colors=ColorPair(fg=star_color))
            character.animation.activate_scene(starting_scn)
            if character not in self.blackhole_chars:
                starfield_coord = self.terminal.canvas.random_coord()
                character.motion.set_coordinate(starfield_coord)
                if starfield_coord.row > self.terminal.canvas.center_row:
                    if starfield_coord.column in range(
                        round(self.terminal.canvas.right * 0.4),
                        round(self.terminal.canvas.right * 0.7),
                    ):
                        # if within the top center 40% of the screen
                        control_point = Coord(self.terminal.canvas.center.column, starfield_coord.row)
                    else:
                        control_point = Coord(starfield_coord.column, self.terminal.canvas.center_row)

                elif starfield_coord.row < self.terminal.canvas.center_row:
                    if starfield_coord.column in range(
                        round(self.terminal.canvas.right * 0.4),
                        round(self.terminal.canvas.right * 0.7),
                    ):
                        # if within the bottom center 40% of the screen
                        control_point = Coord(self.terminal.canvas.center.column, starfield_coord.row)
                    else:
                        control_point = Coord(starfield_coord.column, self.terminal.canvas.center_row)
                else:
                    control_point = self.terminal.canvas.center
                singularity_path = character.motion.new_path(path_id="singularity", speed=0.3, ease=easing.in_expo)
                singularity_path.new_waypoint(self.terminal.canvas.center, bezier_control=control_point)
                consumed_scn = character.animation.new_scene()
                for color in gradient_map[star_color]:
                    consumed_scn.add_frame(star_symbol, 1, colors=ColorPair(fg=color))
                consumed_scn.add_frame(" ", 1)
                consumed_scn.sync = Scene.SyncMetric.DISTANCE
                character.event_handler.register_event(
                    EventHandler.Event.PATH_ACTIVATED,
                    singularity_path,
                    EventHandler.Action.SET_LAYER,
                    2,
                )
                character.event_handler.register_event(
                    EventHandler.Event.PATH_ACTIVATED,
                    singularity_path,
                    EventHandler.Action.ACTIVATE_SCENE,
                    consumed_scn,
                )
                self.awaiting_consumption_chars.append(character)
        random.shuffle(self.awaiting_consumption_chars)

    def rotate_blackhole(self) -> None:
        """Rotate the blackhole characters."""
        for character in self.blackhole_chars:
            character.motion.activate_path(character.motion.query_path("blackhole_rotation"))
            self.active_characters.add(character)

    def collapse_blackhole(self) -> None:
        """Collapse the blackhole characters."""
        black_hole_ring_positions = geometry.find_coords_on_circle(
            self.terminal.canvas.center,
            self.blackhole_radius + 3,
            len(self.blackhole_chars),
        )
        unstable_symbols = ["◦", "◎", "◉", "●", "◉", "◎", "◦"]
        point_char_made = False
        for character in self.blackhole_chars:
            next_pos = black_hole_ring_positions.pop(0)
            expand_path = character.motion.new_path(speed=0.1, ease=easing.in_expo)
            expand_path.new_waypoint(next_pos)
            collapse_path = character.motion.new_path(speed=0.3, ease=easing.in_expo)
            collapse_path.new_waypoint(self.terminal.canvas.center)
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE,
                expand_path,
                EventHandler.Action.ACTIVATE_PATH,
                collapse_path,
            )
            if not point_char_made:
                point_scn = character.animation.new_scene()
                for _ in range(3):
                    for symbol in unstable_symbols:
                        point_scn.add_frame(
                            symbol,
                            6,
                            colors=ColorPair(fg=random.choice(self.config.star_colors)),
                        )
                character.event_handler.register_event(
                    EventHandler.Event.PATH_COMPLETE,
                    collapse_path,
                    EventHandler.Action.ACTIVATE_SCENE,
                    point_scn,
                )
                character.event_handler.register_event(
                    EventHandler.Event.PATH_COMPLETE,
                    collapse_path,
                    EventHandler.Action.SET_LAYER,
                    3,
                )
                point_char_made = True

            character.motion.activate_path(expand_path)
            self.active_characters.add(character)

    def explode_singularity(self) -> None:
        """Explode the singularity characters."""
        star_colors = [
            Color("ffcc0d"),
            Color("ff7326"),
            Color("ff194d"),
            Color("bf2669"),
            Color("702a8c"),
            Color("049dbf"),
        ]
        for character in self.terminal.get_characters():
            nearby_coord = geometry.find_coords_on_circle(character.input_coord, 3, 5)[random.randrange(0, 5)]
            nearby_path = character.motion.new_path(speed=random.randint(2, 3) / 10, ease=easing.out_expo)
            nearby_path.new_waypoint(nearby_coord)
            input_path = character.motion.new_path(speed=random.randint(3, 5) / 100, ease=easing.in_cubic)
            input_path.new_waypoint(character.input_coord)
            explode_scn = character.animation.new_scene()
            explode_star_color = random.choice(star_colors)
            explode_scn.add_frame(character.input_symbol, 1, colors=ColorPair(fg=explode_star_color))
            cooling_scn = character.animation.new_scene()
            if self.terminal.config.existing_color_handling == "dynamic" and self.preexisting_colors_present:
                if not any((character.animation.input_fg_color, character.animation.input_bg_color)):
                    cooling_scn.add_frame(character.input_symbol, 1, colors=ColorPair())
                else:
                    cooling_gradient_fg = None
                    cooling_gradient_bg = None
                    if character.animation.input_fg_color:
                        cooling_gradient_fg = Gradient(
                            explode_star_color,
                            character.animation.input_fg_color,
                            steps=10,
                        )
                    if character.animation.input_bg_color:
                        cooling_gradient_bg = Gradient(
                            explode_star_color,
                            character.animation.input_bg_color,
                            steps=10,
                        )
                    cooling_scn.apply_gradient_to_symbols(
                        character.input_symbol,
                        20,
                        fg_gradient=cooling_gradient_fg,
                        bg_gradient=cooling_gradient_bg,
                    )
            else:
                cooling_gradient = Gradient(explode_star_color, self.character_final_color_map[character], steps=10)
                cooling_scn.apply_gradient_to_symbols(character.input_symbol, 20, fg_gradient=cooling_gradient)
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE,
                nearby_path,
                EventHandler.Action.ACTIVATE_PATH,
                input_path,
            )
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE,
                nearby_path,
                EventHandler.Action.ACTIVATE_SCENE,
                cooling_scn,
            )
            character.animation.activate_scene(explode_scn)
            character.motion.activate_path(nearby_path)
            self.active_characters.add(character)

    def build(self) -> None:
        """Build the Blackhole effect."""
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
        self.prepare_blackhole()
        self.formation_delay = max(100 // len(self.blackhole_chars), 10)
        self.f_delay = self.formation_delay
        self.next_char_consuming_delay = 0
        self.max_consume = max(min(int(0.1 * len(self.terminal._input_characters)), 15), 2)
        self.phase = "forming"
        self.awaiting_blackhole_chars = list(self.blackhole_chars)

    def __next__(self) -> str:
        """Return the next frame in the Blackhole effect."""
        if self.active_characters or self.phase != "complete":
            if self.phase == "forming":
                if self.awaiting_blackhole_chars:
                    if not self.f_delay:
                        next_char = self.awaiting_blackhole_chars.pop(0)
                        next_char.motion.activate_path(next_char.motion.query_path("blackhole"))
                        next_char.animation.activate_scene(next_char.animation.query_scene("blackhole"))
                        self.active_characters.add(next_char)
                        self.f_delay = self.formation_delay
                    else:
                        self.f_delay -= 1
                elif not self.active_characters:
                    self.rotate_blackhole()
                    self.phase = "consuming"
            elif self.phase == "consuming":
                if self.awaiting_consumption_chars:
                    if not self.next_char_consuming_delay:
                        for _ in range(random.randrange(1, self.max_consume)):
                            if self.awaiting_consumption_chars:
                                next_char = self.awaiting_consumption_chars.pop(0)
                                next_char.motion.activate_path(next_char.motion.query_path("singularity"))
                                self.active_characters.add(next_char)
                            else:
                                break
                        self.max_consume += 1
                        self.next_char_consuming_delay = random.randrange(0, 10)
                    else:
                        self.next_char_consuming_delay -= 1

                elif all(character in self.blackhole_chars for character in self.active_characters):
                    self.phase = "collapsing"

            elif self.phase == "collapsing":
                self.collapse_blackhole()
                self.phase = "exploding"
            elif self.phase == "exploding" and all(
                character.motion.active_path is None and character.animation.active_scene is None
                for character in self.blackhole_chars
            ):
                self.explode_singularity()
                self.phase = "complete"

            self.update()
            return self.frame

        raise StopIteration


class Blackhole(BaseEffect[BlackholeConfig]):
    """Creates a blackhole in a starfield, consumes the stars, explodes the input data back into position.

    Attributes:
        effect_config (BlackholeConfig): Configuration for the Blackhole effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    @property
    def _config_cls(self) -> type[BlackholeConfig]:
        return BlackholeConfig

    @property
    def _iterator_cls(self) -> type[BlackholeIterator]:
        return BlackholeIterator
