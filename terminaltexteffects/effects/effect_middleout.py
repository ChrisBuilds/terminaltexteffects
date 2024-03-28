import typing
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils import easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return MiddleoutEffect, MiddleoutEffectArgs


@argclass(
    name="middleout",
    formatter_class=arg_validators.CustomFormatter,
    help="Text expands in a single row or column in the middle of the output area then out.",
    description="middleout | Text expands in a single row or column in the middle of the output area then out.",
    epilog=f"""{arg_validators.EASING_EPILOG}
Example: terminaltexteffects middleout --starting-color 8A008A --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --expand-direction vertical --center-movement-speed 0.35 --full-movement-speed 0.35 --center-easing IN_OUT_SINE --full-easing IN_OUT_SINE""",
)
@dataclass
class MiddleoutEffectArgs(ArgsDataClass):
    starting_color: graphics.Color = ArgField(
        cmd_name="--starting-color",
        type_parser=arg_validators.Color.type_parser,
        default="ffffff",
        metavar=arg_validators.Color.METAVAR,
        help="Color for the initial text in the center of the output area.",
    )  # type: ignore[assignment]
    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name="--final-gradient-stops",
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("8A008A", "00D1FF", "FFFFFF"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=arg_validators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=arg_validators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.VERTICAL,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the gradient for the final color.",
    )  # type: ignore[assignment]
    expand_direction: str = ArgField(
        cmd_name="--expand-direction",
        default="vertical",
        choices=["vertical", "horizontal"],
        help="Direction the text will expand.",
    )  # type: ignore[assignment]
    center_movement_speed: float = ArgField(
        cmd_name="--center-movement-speed",
        type_parser=arg_validators.PositiveFloat.type_parser,
        default=0.35,
        metavar=arg_validators.PositiveFloat.METAVAR,
        help="Speed of the characters during the initial expansion of the center vertical/horiztonal line. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )  # type: ignore[assignment]
    full_movement_speed: float = ArgField(
        cmd_name="--full-movement-speed",
        type_parser=arg_validators.PositiveFloat.type_parser,
        default=0.35,
        metavar=arg_validators.PositiveFloat.METAVAR,
        help="Speed of the characters during the final full expansion. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )  # type: ignore[assignment]
    center_easing: typing.Callable = ArgField(
        cmd_name="--center-easing",
        default=easing.in_out_sine,
        type_parser=arg_validators.Ease.type_parser,
        help="Easing function to use for initial expansion.",
    )  # type: ignore[assignment]
    full_easing: typing.Callable = ArgField(
        cmd_name="--full-easing",
        default=easing.in_out_sine,
        type_parser=arg_validators.Ease.type_parser,
        help="Easing function to use for full expansion.",
    )  # type: ignore[assignment]

    @classmethod
    def get_effect_class(cls):
        return MiddleoutEffect


class MiddleoutEffect:
    """Effect that expands a single row and column followed by the rest of the output area"""

    def __init__(self, terminal: Terminal, args: MiddleoutEffectArgs):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_data(self) -> None:
        """Prepares the data for the effect."""
        final_gradient = graphics.Gradient(*self.args.final_gradient_stops, steps=self.args.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.args.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
            character.motion.set_coordinate(self.terminal.output_area.center)
            # setup waypoints
            if self.args.expand_direction == "vertical":
                column = character.input_coord.column
                row = self.terminal.output_area.center_row
            else:
                column = self.terminal.output_area.center_column
                row = character.input_coord.row
            center_path = character.motion.new_path(speed=self.args.center_movement_speed, ease=self.args.center_easing)
            center_path.new_waypoint(Coord(column, row))
            full_path = character.motion.new_path(
                id="full", speed=self.args.full_movement_speed, ease=self.args.full_easing
            )
            full_path.new_waypoint(character.input_coord, id="full")

            # setup scenes
            full_scene = character.animation.new_scene(id="full")
            full_gradient = graphics.Gradient(
                self.args.starting_color, self.character_final_color_map[character], steps=10
            )
            full_scene.apply_gradient_to_symbols(full_gradient, character.input_symbol, 10)

            # initialize character state
            character.motion.activate_path(center_path)
            character.animation.set_appearance(character.input_symbol, self.args.starting_color)
            self.terminal.set_character_visibility(character, True)
            self.active_chars.append(character)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        final = False
        while self.pending_chars or self.active_chars:
            if all([character.motion.active_path is None for character in self.active_chars]):
                final = True
                for character in self.active_chars:
                    character.motion.activate_path(character.motion.query_path("full"))
                    character.animation.activate_scene(character.animation.query_scene("full"))
            self.terminal.print()
            self.animate_chars()
            if final:
                self.active_chars = [character for character in self.active_chars if character.is_active]

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method."""
        for character in self.active_chars:
            character.tick()
