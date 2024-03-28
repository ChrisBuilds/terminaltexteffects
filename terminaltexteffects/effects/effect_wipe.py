import typing
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils import graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.terminal import Terminal


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return WipeEffect, WipeEffectArgs


@argclass(
    name="wipe",
    formatter_class=arg_validators.CustomFormatter,
    help="Wipes the text across the terminal to reveal characters.",
    description="wipe | Wipes the text across the terminal to reveal characters.",
    epilog="""Example: terminaltexteffects wipe --wipe-direction diagonal_bottom_left_to_top_right --final-gradient-stops 833ab4 fd1d1d fcb045 --final-gradient-steps 12 --final-gradient-frames 5 --wipe-delay 0""",
)
@dataclass
class WipeEffectArgs(ArgsDataClass):
    wipe_direction: str = ArgField(
        cmd_name="--wipe-direction",
        default="diagonal_bottom_left_to_top_right",
        choices=[
            "column_left_to_right",
            "column_right_to_left",
            "row_top_to_bottom",
            "row_bottom_to_top",
            "diagonal_top_left_to_bottom_right",
            "diagonal_bottom_left_to_top_right",
            "diagonal_top_right_to_bottom_left",
            "diagonal_bottom_right_to_top_left",
        ],
        help="Direction the text will wipe.",
    )  # type: ignore[assignment]
    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name="--final-gradient-stops",
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("833ab4", "fd1d1d", "fcb045"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the wipe gradient.",
    )  # type: ignore[assignment]
    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=arg_validators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    final_gradient_frames: int = ArgField(
        cmd_name="--final-gradient-frames",
        type_parser=arg_validators.PositiveInt.type_parser,
        default=5,
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
    wipe_delay: int = ArgField(
        cmd_name="--wipe-delay",
        type_parser=arg_validators.NonNegativeInt.type_parser,
        default=0,
        metavar=arg_validators.NonNegativeInt.METAVAR,
        help="Number of animation cycles to wait before adding the next character group. Increase, to slow down the effect.",
    )  # type: ignore[assignment]

    @classmethod
    def get_effect_class(cls):
        return WipeEffect


class WipeEffect:
    """Effect that performs a wipe across the terminal to reveal characters."""

    def __init__(self, terminal: Terminal, args: WipeEffectArgs):
        self.terminal = terminal
        self.args = args
        self.pending_groups: list[list[EffectCharacter]] = []
        self.active_chars: list[EffectCharacter] = []
        self.direction = self.args.wipe_direction
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_data(self) -> None:
        final_gradient = graphics.Gradient(*self.args.final_gradient_stops, steps=self.args.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.args.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
        sort_map = {
            "column_left_to_right": self.terminal.CharacterGroup.COLUMN_LEFT_TO_RIGHT,
            "column_right_to_left": self.terminal.CharacterGroup.COLUMN_RIGHT_TO_LEFT,
            "row_top_to_bottom": self.terminal.CharacterGroup.ROW_TOP_TO_BOTTOM,
            "row_bottom_to_top": self.terminal.CharacterGroup.ROW_BOTTOM_TO_TOP,
            "diagonal_top_left_to_bottom_right": self.terminal.CharacterGroup.DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT,
            "diagonal_bottom_left_to_top_right": self.terminal.CharacterGroup.DIAGONAL_BOTTOM_LEFT_TO_TOP_RIGHT,
            "diagonal_top_right_to_bottom_left": self.terminal.CharacterGroup.DIAGONAL_TOP_RIGHT_TO_BOTTOM_LEFT,
            "diagonal_bottom_right_to_top_left": self.terminal.CharacterGroup.DIAGONAL_BOTTOM_RIGHT_TO_TOP_LEFT,
        }
        for group in self.terminal.get_characters_grouped(sort_map[self.direction]):
            for character in group:
                wipe_scn = character.animation.new_scene()
                wipe_gradient = graphics.Gradient(
                    final_gradient.spectrum[0],
                    self.character_final_color_map[character],
                    steps=self.args.final_gradient_steps,
                )
                wipe_scn.apply_gradient_to_symbols(
                    wipe_gradient, character.input_symbol, self.args.final_gradient_frames
                )
                character.animation.activate_scene(wipe_scn)
            self.pending_groups.append(group)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        wipe_delay = self.args.wipe_delay
        while self.pending_groups or self.active_chars:
            if not wipe_delay:
                if self.pending_groups:
                    next_group = self.pending_groups.pop(0)
                    for character in next_group:
                        self.terminal.set_character_visibility(character, True)
                        self.active_chars.append(character)
                wipe_delay = self.args.wipe_delay
            else:
                wipe_delay -= 1
            self.terminal.print()
            self.animate_chars()

            self.active_chars = [character for character in self.active_chars if character.is_active]

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method on all active characters."""
        for character in self.active_chars:
            character.tick()
