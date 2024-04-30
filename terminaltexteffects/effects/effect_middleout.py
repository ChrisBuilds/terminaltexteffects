"""Text expands in a single row or column in the middle of the output area then out.

Classes:
    MiddleOut: Text expands in a single row or column in the middle of the output area then out.
    MiddleOutConfig: Configuration for the Middleout effect.
    MiddleOutIterator: Iterates over the effect's frames. Does not normally need to be called directly.

"""

import typing
from dataclasses import dataclass

import terminaltexteffects.utils.argvalidators as argvalidators
from terminaltexteffects.engine.base_character import EffectCharacter
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return MiddleOut, MiddleOutConfig


@argclass(
    name="middleout",
    help="Text expands in a single row or column in the middle of the output area then out.",
    description="middleout | Text expands in a single row or column in the middle of the output area then out.",
    epilog=f"""{argvalidators.EASING_EPILOG}
Example: terminaltexteffects middleout --starting-color 8A008A --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --expand-direction vertical --center-movement-speed 0.35 --full-movement-speed 0.35 --center-easing IN_OUT_SINE --full-easing IN_OUT_SINE""",
)
@dataclass
class MiddleOutConfig(ArgsDataClass):
    """Configuration for the Middleout effect.

    Attributes:
        starting_color (graphics.Color): Color for the initial text in the center of the output area.
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the final gradient.
        expand_direction (str): Direction the text will expand. Choices: vertical, horizontal.
        center_movement_speed (float): Speed of the characters during the initial expansion of the center vertical/horiztonal. Valid values are n > 0."""

    starting_color: graphics.Color = ArgField(
        cmd_name="--starting-color",
        type_parser=argvalidators.ColorArg.type_parser,
        default="ffffff",
        metavar=argvalidators.ColorArg.METAVAR,
        help="Color for the initial text in the center of the output area.",
    )  # type: ignore[assignment]
    "graphics.Color : Color for the initial text in the center of the output area."

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name="--final-gradient-stops",
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=("8A008A", "00D1FF", "FFFFFF"),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] : Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.VERTICAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "graphics.Gradient.Direction : Direction of the final gradient."

    expand_direction: str = ArgField(
        cmd_name="--expand-direction",
        default="vertical",
        choices=["vertical", "horizontal"],
        help="Direction the text will expand.",
    )  # type: ignore[assignment]
    "str : Direction the text will expand."

    center_movement_speed: float = ArgField(
        cmd_name="--center-movement-speed",
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=0.35,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Speed of the characters during the initial expansion of the center vertical/horiztonal line. ",
    )  # type: ignore[assignment]
    "float : Speed of the characters during the initial expansion of the center vertical/horiztonal line. "

    full_movement_speed: float = ArgField(
        cmd_name="--full-movement-speed",
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=0.35,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Speed of the characters during the final full expansion. ",
    )  # type: ignore[assignment]
    "float : Speed of the characters during the final full expansion. "

    center_easing: easing.EasingFunction = ArgField(
        cmd_name="--center-easing",
        default=easing.in_out_sine,
        type_parser=argvalidators.Ease.type_parser,
        help="Easing function to use for initial expansion.",
    )  # type: ignore[assignment]
    "easing.EasingFunction : Easing function to use for initial expansion."

    full_easing: easing.EasingFunction = ArgField(
        cmd_name="--full-easing",
        default=easing.in_out_sine,
        type_parser=argvalidators.Ease.type_parser,
        help="Easing function to use for full expansion.",
    )  # type: ignore[assignment]
    "easing.EasingFunction : Easing function to use for full expansion."

    @classmethod
    def get_effect_class(cls):
        return MiddleOut


class MiddleOutIterator(BaseEffectIterator[MiddleOutConfig]):
    def __init__(self, effect: "MiddleOut"):
        super().__init__(effect)
        self._pending_chars: list[EffectCharacter] = []
        self._active_chars: list[EffectCharacter] = []
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}
        self._phase = "center"
        self._build()

    def _build(self) -> None:
        final_gradient = graphics.Gradient(*self._config.final_gradient_stops, steps=self._config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self._terminal.output_area.top, self._terminal.output_area.right, self._config.final_gradient_direction
        )
        for character in self._terminal.get_characters():
            self._character_final_color_map[character] = final_gradient_mapping[character.input_coord]
            character.motion.set_coordinate(self._terminal.output_area.center)
            # setup waypoints
            if self._config.expand_direction == "vertical":
                column = character.input_coord.column
                row = self._terminal.output_area.center_row
            else:
                column = self._terminal.output_area.center_column
                row = character.input_coord.row
            center_path = character.motion.new_path(
                speed=self._config.center_movement_speed, ease=self._config.center_easing
            )
            center_path.new_waypoint(Coord(column, row))
            full_path = character.motion.new_path(
                id="full", speed=self._config.full_movement_speed, ease=self._config.full_easing
            )
            full_path.new_waypoint(character.input_coord, id="full")

            # setup scenes
            full_scene = character.animation.new_scene(id="full")
            full_gradient = graphics.Gradient(
                self._config.starting_color, self._character_final_color_map[character], steps=10
            )
            full_scene.apply_gradient_to_symbols(full_gradient, character.input_symbol, 10)

            # initialize character state
            character.motion.activate_path(center_path)
            character.animation.set_appearance(character.input_symbol, self._config.starting_color)
            self._terminal.set_character_visibility(character, True)
            self._active_chars.append(character)

    def __next__(self) -> str:
        if self._active_chars:
            if (
                all([character.motion.active_path is None for character in self._active_chars])
                and self._phase == "center"
            ):
                for character in self._active_chars:
                    character.motion.activate_path(character.motion.query_path("full"))
                    character.animation.activate_scene(character.animation.query_scene("full"))
                self._phase = "full"
            for character in self._active_chars:
                character.tick()
            if self._phase == "full":
                self._active_chars = [character for character in self._active_chars if character.is_active]
            return self._terminal.get_formatted_output_string()
        else:
            raise StopIteration


class MiddleOut(BaseEffect[MiddleOutConfig]):
    """Text expands in a single row or column in the middle of the output area then out.

    Attributes:
        effect_config (MiddleOutConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.
    """

    _config_cls = MiddleOutConfig
    _iterator_cls = MiddleOutIterator

    def __init__(self, input_data: str) -> None:
        """Initialize the effect with the provided input data.

        Args:
            input_data (str): The input data to use for the effect."""
        super().__init__(input_data)
