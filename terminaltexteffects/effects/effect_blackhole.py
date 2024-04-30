"""
Creates a blackhole in a starfield, consumes the stars, explodes the input data back into position.

Classes:
    BlackholeConfig: Configuration for the Blackhole effect.
    Blackhole: Creates a blackhole in a starfield, consumes the stars, explodes the input data back into position.
    BlackholeIterator: Iterator for the Blackhole effect. Does not normally need to be called directly.

"""

import random
import typing
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.engine import animation
from terminaltexteffects.engine.base_character import EffectCharacter, EventHandler
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import easing, geometry, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return Blackhole, BlackholeConfig


@argclass(
    name="blackhole",
    help="Characters are consumed by a black hole and explode outwards.",
    description="blackhole | Characters are consumed by a black hole and explode outwards.",
    epilog="""Example: terminaltexteffects blackhole --star-colors ffcc0d ff7326 ff194d bf2669 702a8c 049dbf --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --final-gradient-direction vertical""",
)
@dataclass
class BlackholeConfig(ArgsDataClass):
    """Configuration for the Blackhole effect.

    Attributes:
        blackhole_color (graphics.Color): Color for the stars that comprise the blackhole border.
        star_colors (tuple[graphics.Color, ...]): Tuple of colors from which character colors will be chosen and applied after the explosion, but before the cooldown to final color.
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the character gradient. If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the final gradient."""

    blackhole_color: graphics.Color = ArgField(
        cmd_name=["--blackhole-color"],
        type_parser=arg_validators.Color.type_parser,
        default="ffffff",
        metavar=arg_validators.Color.METAVAR,
        help="Color for the stars that comprise the blackhole border.",
    )  # type: ignore[assignment]

    "graphics.Color : Color for the stars that comprise the blackhole border."

    star_colors: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--star-colors"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("ffcc0d", "ff7326", "ff194d", "bf2669", "702a8c", "049dbf"),
        metavar=arg_validators.Color.METAVAR,
        help="List of colors from which character colors will be chosen and applied after the explosion, but before the cooldown to final color.",
    )  # type: ignore[assignment]

    "tuple[graphics.Color, ...] : Tuple of colors from which character colors will be chosen and applied after the explosion, but before the cooldown to final color."

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("8A008A", "00D1FF", "ffffff"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]

    "tuple[graphics.Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name=["--final-gradient-steps"],
        type_parser=arg_validators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]

    "tuple[int, ...] : Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=arg_validators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.DIAGONAL,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]

    "graphics.Gradient.Direction : Direction of the final gradient."

    @classmethod
    def get_effect_class(cls):
        return Blackhole


class BlackholeIterator(BaseEffectIterator[BlackholeConfig]):
    def __init__(self, effect: "Blackhole") -> None:
        super().__init__(effect)
        self._pending_chars: list[EffectCharacter] = []
        self._active_chars: list[EffectCharacter] = []
        self._blackhole_chars: list[EffectCharacter] = []
        self._awaiting_consumption_chars: list[EffectCharacter] = []
        self._blackhole_radius = max(
            min(
                round(self._terminal.output_area.right * 0.3),
                round(self._terminal.output_area.top * 0.3),
            ),
            3,
        )
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}
        self._build()

    def _prepare_blackhole(self) -> None:
        star_symbols = [
            "*",
            "✸",
            "✺",
            "✹",
            "✷",
            "✵",
            "✴",
            "✶",
            "⋆",
            "'",
            ".",
            "⬫",
            "⬪",
            "⬩",
            "⬨",
            "⬧",
            "⬦",
            "⬥",
        ]
        starfield_colors = graphics.Gradient("4a4a4d", "ffffff", steps=6).spectrum
        gradient_map = {}
        for color in starfield_colors:
            gradient_map[color] = graphics.Gradient(color, "000000", steps=10)
        available_chars = list(self._terminal._input_characters)
        while len(self._blackhole_chars) < self._blackhole_radius * 3 and available_chars:
            self._blackhole_chars.append(available_chars.pop(random.randrange(0, len(available_chars))))
        black_hole_ring_positions = geometry.find_coords_on_circle(
            self._terminal.output_area.center,
            self._blackhole_radius,
            len(self._blackhole_chars),
        )
        for position_index, character in enumerate(self._blackhole_chars):
            starting_pos = black_hole_ring_positions[position_index]
            blackhole_path = character.motion.new_path(id="blackhole", speed=0.5, ease=easing.in_out_sine)
            blackhole_path.new_waypoint(starting_pos)
            blackhole_scn = character.animation.new_scene(id="blackhole")
            blackhole_scn.add_frame("✸", 1, color=self._config.blackhole_color)
            character.event_handler.register_event(
                EventHandler.Event.PATH_ACTIVATED,
                blackhole_path,
                EventHandler.Action.SET_LAYER,
                1,
            )
            # make rotation waypoints
            blackhole_rotation_path = character.motion.new_path(id="blackhole_rotation", speed=0.2, loop=True)
            for coord in black_hole_ring_positions[position_index:] + black_hole_ring_positions[:position_index]:
                blackhole_rotation_path.new_waypoint(coord, id=str(len(blackhole_rotation_path.waypoints)))
        for character in self._terminal.get_characters():
            self._terminal.set_character_visibility(character, True)
            starting_scn = character.animation.new_scene()
            star_symbol = random.choice(star_symbols)
            star_color = random.choice(starfield_colors)
            starting_scn.add_frame(star_symbol, 1, color=star_color)
            character.animation.activate_scene(starting_scn)
            if character not in self._blackhole_chars:
                starfield_coord = self._terminal.output_area.random_coord()
                character.motion.set_coordinate(starfield_coord)
                if starfield_coord.row > self._terminal.output_area.center_row:
                    if starfield_coord.column in range(
                        round(self._terminal.output_area.right * 0.4),
                        round(self._terminal.output_area.right * 0.7),
                    ):
                        # if within the top center 40% of the screen
                        control_point = Coord(self._terminal.output_area.center.column, starfield_coord.row)
                    else:
                        control_point = Coord(starfield_coord.column, self._terminal.output_area.center_row)

                elif starfield_coord.row < self._terminal.output_area.center_row:
                    if starfield_coord.column in range(
                        round(self._terminal.output_area.right * 0.4),
                        round(self._terminal.output_area.right * 0.7),
                    ):
                        # if within the bottom center 40% of the screen
                        control_point = Coord(self._terminal.output_area.center.column, starfield_coord.row)
                    else:
                        control_point = Coord(starfield_coord.column, self._terminal.output_area.center_row)
                else:
                    control_point = self._terminal.output_area.center
                singularity_path = character.motion.new_path(id="singularity", speed=0.3, ease=easing.in_expo)
                singularity_path.new_waypoint(self._terminal.output_area.center, bezier_control=control_point)
                consumed_scn = character.animation.new_scene()
                for color in gradient_map[star_color]:
                    consumed_scn.add_frame(star_symbol, 1, color=color)
                consumed_scn.add_frame(" ", 1)
                consumed_scn.sync = animation.SyncMetric.DISTANCE
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
                self._awaiting_consumption_chars.append(character)
        random.shuffle(self._awaiting_consumption_chars)

    def _rotate_blackhole(self) -> None:
        for character in self._blackhole_chars:
            character.motion.activate_path(character.motion.query_path("blackhole_rotation"))
            self._active_chars.append(character)

    def _collapse_blackhole(self) -> None:
        black_hole_ring_positions = geometry.find_coords_on_circle(
            self._terminal.output_area.center,
            self._blackhole_radius + 3,
            len(self._blackhole_chars),
        )
        unstable_symbols = ["◦", "◎", "◉", "●", "◉", "◎", "◦"]
        point_char_made = False
        for character in self._blackhole_chars:
            next_pos = black_hole_ring_positions.pop(0)
            expand_path = character.motion.new_path(speed=0.1, ease=easing.in_expo)
            expand_path.new_waypoint(next_pos)
            collapse_path = character.motion.new_path(speed=0.3, ease=easing.in_expo)
            collapse_path.new_waypoint(self._terminal.output_area.center)
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
                        point_scn.add_frame(symbol, 6, color=random.choice(self._config.star_colors))
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
            self._active_chars.append(character)

    def _explode_singularity(self) -> None:
        star_colors = ["ffcc0d", "ff7326", "ff194d", "bf2669", "702a8c" "049dbf"]
        for character in self._terminal.get_characters():
            nearby_coord = geometry.find_coords_on_circle(character.input_coord, 3, 5)[random.randrange(0, 5)]
            nearby_path = character.motion.new_path(speed=random.randint(2, 3) / 10, ease=easing.out_expo)
            nearby_path.new_waypoint(nearby_coord)
            input_path = character.motion.new_path(speed=random.randint(3, 5) / 100, ease=easing.in_cubic)
            input_path.new_waypoint(character.input_coord)
            explode_scn = character.animation.new_scene()
            explode_star_color = random.choice(star_colors)
            explode_scn.add_frame(character.input_symbol, 1, color=explode_star_color)
            cooling_scn = character.animation.new_scene()
            cooling_gradient = graphics.Gradient(
                explode_star_color, self._character_final_color_map[character], steps=10
            )
            cooling_scn.apply_gradient_to_symbols(cooling_gradient, character.input_symbol, 20)
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
            self._active_chars.append(character)

    def _build(self) -> None:
        final_gradient = graphics.Gradient(*self._config.final_gradient_stops, steps=self._config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self._terminal.output_area.top, self._terminal.output_area.right, self._config.final_gradient_direction
        )
        for character in self._terminal.get_characters():
            self._character_final_color_map[character] = final_gradient_mapping[character.input_coord]
        self._prepare_blackhole()
        self.formation_delay = max(100 // len(self._blackhole_chars), 10)
        self.f_delay = self.formation_delay
        self.next_char_consuming_delay = 0
        self.max_consume = max(min(int(0.1 * len(self._terminal._input_characters)), 15), 2)
        self.phase = "forming"
        self.awaiting_blackhole_chars = list(self._blackhole_chars)

    def __next__(self) -> str:
        if self._active_chars or self.phase != "complete":
            if self.phase == "forming":
                if self.awaiting_blackhole_chars:
                    if not self.f_delay:
                        next_char = self.awaiting_blackhole_chars.pop(0)
                        next_char.motion.activate_path(next_char.motion.query_path("blackhole"))
                        next_char.animation.activate_scene(next_char.animation.query_scene("blackhole"))
                        self._active_chars.append(next_char)
                        self.f_delay = self.formation_delay
                    else:
                        self.f_delay -= 1
                else:
                    if not self._active_chars:
                        self._rotate_blackhole()
                        self.phase = "consuming"
            elif self.phase == "consuming":
                if self._awaiting_consumption_chars:
                    if not self.next_char_consuming_delay:
                        for _ in range(random.randrange(1, self.max_consume)):
                            if self._awaiting_consumption_chars:
                                next_char = self._awaiting_consumption_chars.pop(0)
                                next_char.motion.activate_path(next_char.motion.query_path("singularity"))
                                self._active_chars.append(next_char)
                            else:
                                break
                        self.max_consume += 1
                        self.next_char_consuming_delay = random.randrange(0, 10)
                    else:
                        self.next_char_consuming_delay -= 1

                else:
                    if all(character in self._blackhole_chars for character in self._active_chars):
                        self.phase = "collapsing"

            elif self.phase == "collapsing":
                self._collapse_blackhole()
                self.phase = "exploding"
            elif self.phase == "exploding":
                if all(
                    [
                        character.motion.active_path is None and character.animation.active_scene is None
                        for character in self._blackhole_chars
                    ]
                ):
                    self._explode_singularity()
                    self.phase = "complete"

            for character in self._active_chars:
                character.tick()
            next_frame = self._terminal.get_formatted_output_string()

            self._active_chars = [character for character in self._active_chars if character.is_active]
            return next_frame

        else:
            raise StopIteration


class Blackhole(BaseEffect[BlackholeConfig]):
    """Creates a blackhole in a starfield, consumes the stars, explodes the input data back into position.

    Attributes:
        effect_config (BlackholeConfig): Configuration for the Blackhole effect.
        terminal_config (TerminalConfig): Configuration for the terminal.
    """

    _config_cls = BlackholeConfig
    _iterator_cls = BlackholeIterator

    def __init__(self, input_data: str) -> None:
        """Initializes the Blackhole effect with the provided input data.

        Args:
            input_data (str): The input data to use for the Blackhole effect.
        """
        super().__init__(input_data)
