"""Effect that pours the characters into position from the top, bottom, left, or right."""

import typing
from dataclasses import dataclass
from enum import Enum, auto

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils import easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return PourEffect, PourEffectArgs


@argclass(
    name="pour",
    formatter_class=arg_validators.CustomFormatter,
    help="Pours the characters into position from the given direction.",
    description="pour | Pours the characters into position from the given direction.",
    epilog=f"""{arg_validators.EASING_EPILOG}
Example: terminaltexteffects pour --pour-direction down --movement-speed 0.2 --gap 1 --starting-color FFFFFF --final-gradient-stops 8A008A 00D1FF FFFFFF --easing IN_QUAD""",
)
@dataclass
class PourEffectArgs(ArgsDataClass):
    pour_direction: str = ArgField(
        cmd_name=["--pour-direction"],
        default="down",
        choices=["up", "down", "left", "right"],
        help="Direction the text will pour.",
    )  # type: ignore[assignment]
    pour_speed: int = ArgField(
        cmd_name="--pour-speed",
        type_parser=arg_validators.PositiveInt.type_parser,
        default=1,
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Number of characters poured in per tick. Increase to speed up the effect.",
    )  # type: ignore[assignment]
    movement_speed: float = ArgField(
        cmd_name="--movement-speed",
        type_parser=arg_validators.PositiveFloat.type_parser,
        default=0.2,
        metavar=arg_validators.PositiveFloat.METAVAR,
        help="Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )  # type: ignore[assignment]
    gap: int = ArgField(
        cmd_name="--gap",
        type_parser=arg_validators.NonNegativeInt.type_parser,
        default=1,
        metavar=arg_validators.NonNegativeInt.METAVAR,
        help="Number of frames to wait between each character in the pour effect. Increase to slow down effect and create a more defined back and forth motion.",
    )  # type: ignore[assignment]
    starting_color: graphics.Color = ArgField(
        cmd_name=["--starting-color"],
        type_parser=arg_validators.Color.type_parser,
        default="ffffff",
        metavar=arg_validators.Color.METAVAR,
        help="Color of the characters before the gradient starts.",
    )  # type: ignore[assignment]
    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("8A008A", "00D1FF", "FFFFFF"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient. If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name=["--final-gradient-steps"],
        type_parser=arg_validators.PositiveInt.type_parser,
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    final_gradient_frames: int = ArgField(
        cmd_name=["--final-gradient-frames"],
        type_parser=arg_validators.PositiveInt.type_parser,
        default=10,
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step.",
    )  # type: ignore[assignment]
    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=arg_validators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.VERTICAL,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the gradient for the final color.",
    )  # type: ignore[assignment]
    easing: typing.Callable = ArgField(
        cmd_name="--easing",
        default=easing.in_quad,
        type_parser=arg_validators.Ease.type_parser,
        help="Easing function to use for character movement.",
    )  # type: ignore[assignment]

    @classmethod
    def get_effect_class(cls):
        return PourEffect


class PourDirection(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()


class PourEffect:
    """Effect that pours the characters into position from the top, bottom, left, or right."""

    def __init__(self, terminal: Terminal, args: PourEffectArgs):
        self.terminal = terminal
        self.args = args
        self.pending_groups: list[list[EffectCharacter]] = []
        self.active_characters: list[EffectCharacter] = []
        self.pour_direction = {
            "down": PourDirection.DOWN,
            "up": PourDirection.UP,
            "left": PourDirection.LEFT,
            "right": PourDirection.RIGHT,
        }.get(args.pour_direction, PourDirection.DOWN)
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_data(self) -> None:
        """Prepares the data for the effect by sorting the characters by the pour direction."""
        final_gradient = graphics.Gradient(*self.args.final_gradient_stops, steps=self.args.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.args.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
        sort_map = {
            PourDirection.DOWN: Terminal.CharacterGroup.ROW_BOTTOM_TO_TOP,
            PourDirection.UP: Terminal.CharacterGroup.ROW_TOP_TO_BOTTOM,
            PourDirection.LEFT: Terminal.CharacterGroup.COLUMN_LEFT_TO_RIGHT,
            PourDirection.RIGHT: Terminal.CharacterGroup.COLUMN_RIGHT_TO_LEFT,
        }
        groups = self.terminal.get_characters_grouped(grouping=sort_map[self.pour_direction])
        for i, group in enumerate(groups):
            for character in group:
                self.terminal.set_character_visibility(character, False)
                if self.pour_direction == PourDirection.DOWN:
                    character.motion.set_coordinate(Coord(character.input_coord.column, self.terminal.output_area.top))
                elif self.pour_direction == PourDirection.UP:
                    character.motion.set_coordinate(
                        Coord(character.input_coord.column, self.terminal.output_area.bottom)
                    )
                elif self.pour_direction == PourDirection.LEFT:
                    character.motion.set_coordinate(Coord(self.terminal.output_area.right, character.input_coord.row))
                elif self.pour_direction == PourDirection.RIGHT:
                    character.motion.set_coordinate(Coord(self.terminal.output_area.left, character.input_coord.row))
                input_coord_path = character.motion.new_path(
                    speed=self.args.movement_speed,
                    ease=self.args.easing,
                )
                input_coord_path.new_waypoint(character.input_coord)
                character.motion.activate_path(input_coord_path)

                pour_gradient = graphics.Gradient(
                    self.args.starting_color,
                    self.character_final_color_map[character],
                    steps=self.args.final_gradient_steps,
                )
                pour_scn = character.animation.new_scene()
                pour_scn.apply_gradient_to_symbols(
                    pour_gradient, character.input_symbol, self.args.final_gradient_frames
                )
                character.animation.activate_scene(pour_scn)
            if i % 2 == 0:
                self.pending_groups.append(group)
            else:
                self.pending_groups.append(group[::-1])

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        self.terminal.print()
        current_group = self.pending_groups.pop(0)
        gap = 0
        while self.pending_groups or self.active_characters or current_group:
            if not current_group:
                if self.pending_groups:
                    current_group = self.pending_groups.pop(0)
            if current_group:
                if not gap:
                    for _ in range(self.args.pour_speed):
                        if current_group:
                            next_character = current_group.pop(0)
                            self.terminal.set_character_visibility(next_character, True)
                            self.active_characters.append(next_character)
                    gap = self.args.gap
                else:
                    gap -= 1
            self.animate_chars()
            self.active_characters = [character for character in self.active_characters if character.is_active]
            self.terminal.print()

    def animate_chars(self) -> None:
        """Animates the sliding characters."""
        for character in self.active_characters:
            character.tick()
