import typing
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils import easing, geometry, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.terminal import Terminal


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return SlideEffect, SlideEffectArgs


@argclass(
    name="slide",
    formatter_class=arg_validators.CustomFormatter,
    help="Slide characters into view from outside the terminal.",
    description="slide | Slide characters into view from outside the terminal, grouped by row, column, or diagonal.",
    epilog=f"""{arg_validators.EASING_EPILOG}
Example: terminaltexteffects slide --movement-speed 0.5 --grouping row --final-gradient-stops 833ab4 fd1d1d fcb045 --final-gradient-steps 12 --final-gradient-frames 10 --final-gradient-direction vertical --gap 3 --reverse-direction --merge --movement-easing OUT_QUAD""",
)
@dataclass
class SlideEffectArgs(ArgsDataClass):
    movement_speed: float = ArgField(
        cmd_name="--movement-speed",
        type_parser=arg_validators.PositiveFloat.type_parser,
        default=0.5,
        metavar=arg_validators.PositiveFloat.METAVAR,
        help="Speed of the characters.",
    )  # type: ignore[assignment]
    grouping: str = ArgField(
        cmd_name="--grouping",
        default="row",
        choices=["row", "column", "diagonal"],
        help="Direction to group characters.",
    )  # type: ignore[assignment]
    final_gradient_stops: tuple[int | str, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("833ab4", "fd1d1d", "fcb045"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient. If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=arg_validators.PositiveInt.type_parser,
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    final_gradient_frames: int = ArgField(
        cmd_name="--final-gradient-frames",
        type_parser=arg_validators.PositiveInt.type_parser,
        default=10,
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step.",
    )  # type: ignore[assignment]
    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        default=graphics.Gradient.Direction.VERTICAL,
        type_parser=arg_validators.GradientDirection.type_parser,
        help="Direction of the gradient (vertical, horizontal, diagonal, center).",
    )  # type: ignore[assignment]
    gap: int = ArgField(
        cmd_name="--gap",
        type_parser=arg_validators.NonNegativeInt.type_parser,
        default=3,
        metavar=arg_validators.NonNegativeInt.METAVAR,
        help="Number of frames to wait before adding the next group of characters. Increasing this value creates a more staggered effect.",
    )  # type: ignore[assignment]
    reverse_direction: bool = ArgField(
        cmd_name="--reverse-direction",
        action="store_true",
        help="Reverse the direction of the characters.",
    )  # type: ignore[assignment]
    merge: bool = ArgField(
        cmd_name="--merge",
        action="store_true",
        help="Merge the character groups originating from either side of the terminal. (--reverse-direction is ignored when merging)",
    )  # type: ignore[assignment]
    movement_easing: easing.EasingFunction = ArgField(
        cmd_name=["--movement-easing"],
        default=easing.in_out_quad,
        type_parser=arg_validators.Ease.type_parser,
        metavar=arg_validators.Ease.METAVAR,
        help="Easing function to use for character movement.",
    )  # type: ignore[assignment]

    @classmethod
    def get_effect_class(cls):
        return SlideEffect


class SlideEffect:
    """Effect that slides characters into view from outside the terminal. Characters are grouped by column, row, or diagonal."""

    def __init__(self, terminal: Terminal, args: SlideEffectArgs):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.grouping: str = self.args.grouping
        self.reverse_direction: bool = self.args.reverse_direction
        self.merge: bool = self.args.merge
        self.gradient_stops = self.args.final_gradient_stops
        self.gap = self.args.gap
        self.pending_groups: list[list[EffectCharacter]] = []
        self.easing = self.args.movement_easing
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_data(self) -> None:
        """Prepares the data for the effect by setting starting coordinates and building Paths/Scenes."""
        final_gradient = graphics.Gradient(*self.args.final_gradient_stops, steps=self.args.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.args.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]

        groups: list[list[EffectCharacter]] = []
        if self.grouping == "row":
            groups = self.terminal.get_characters_grouped(self.terminal.CharacterGroup.ROW_TOP_TO_BOTTOM)
        elif self.grouping == "column":
            groups = self.terminal.get_characters_grouped(self.terminal.CharacterGroup.COLUMN_LEFT_TO_RIGHT)
        elif self.grouping == "diagonal":
            groups = self.terminal.get_characters_grouped(
                self.terminal.CharacterGroup.DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT
            )
        for group in groups:
            for character in group:
                input_path = character.motion.new_path(
                    id="input_path", speed=self.args.movement_speed, ease=self.easing
                )
                input_path.new_waypoint(character.input_coord)

        for group_index, group in enumerate(groups):
            if self.grouping == "row":
                if self.merge and group_index % 2 == 0:
                    starting_column = self.terminal.output_area.right + 1
                else:
                    groups[group_index] = groups[group_index][::-1]
                    starting_column = self.terminal.output_area.left - 1
                if self.reverse_direction and not self.merge:
                    groups[group_index] = groups[group_index][::-1]
                    starting_column = self.terminal.output_area.right + 1
                for character in groups[group_index]:
                    character.motion.set_coordinate(geometry.Coord(starting_column, character.input_coord.row))
            elif self.grouping == "column":
                if self.merge and group_index % 2 == 0:
                    starting_row = self.terminal.output_area.bottom - 1
                else:
                    groups[group_index] = groups[group_index][::-1]
                    starting_row = self.terminal.output_area.top + 1
                if self.reverse_direction and not self.merge:
                    groups[group_index] = groups[group_index][::-1]
                    starting_row = self.terminal.output_area.bottom - 1
                for character in groups[group_index]:
                    character.motion.set_coordinate(geometry.Coord(character.input_coord.column, starting_row))
            if self.grouping == "diagonal":
                distance_from_outside_bottom = group[-1].input_coord.row - (self.terminal.output_area.bottom - 1)
                starting_coord = geometry.Coord(
                    group[-1].input_coord.column - distance_from_outside_bottom,
                    group[-1].input_coord.row - distance_from_outside_bottom,
                )
                if self.merge and group_index % 2 == 0:
                    groups[group_index] = groups[group_index][::-1]
                    distance_from_outside = (self.terminal.output_area.top + 1) - group[0].input_coord.row
                    starting_coord = geometry.Coord(
                        group[0].input_coord.column + distance_from_outside,
                        group[0].input_coord.row + distance_from_outside,
                    )
                if self.reverse_direction and not self.merge:
                    groups[group_index] = groups[group_index][::-1]
                    distance_from_outside = (self.terminal.output_area.top + 1) - group[0].input_coord.row
                    starting_coord = geometry.Coord(
                        group[0].input_coord.column + distance_from_outside,
                        group[0].input_coord.row + distance_from_outside,
                    )

                for character in groups[group_index]:
                    character.motion.set_coordinate(starting_coord)
            for character in group:
                gradient_scn = character.animation.new_scene()
                char_gradient = graphics.Gradient(
                    self.gradient_stops[0], self.character_final_color_map[character], steps=10
                )
                gradient_scn.apply_gradient_to_symbols(
                    char_gradient, character.input_symbol, self.args.final_gradient_frames
                )
                character.animation.activate_scene(gradient_scn)

        self.pending_groups = groups

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        active_groups: list[list[EffectCharacter]] = []
        current_gap = 0
        while self.pending_groups or self.active_chars or active_groups:
            if current_gap == self.gap and self.pending_groups:
                active_groups.append(self.pending_groups.pop(0))
                current_gap = 0
            else:
                if self.pending_groups:
                    current_gap += 1
            for group in active_groups:
                if group:
                    next_char = group.pop(0)
                    self.terminal.set_character_visibility(next_char, True)
                    next_char.motion.activate_path(next_char.motion.paths["input_path"])
                    self.active_chars.append(next_char)
            active_groups = [group for group in active_groups if group]
            self.terminal.print()
            self.animate_chars()

            self.active_chars = [character for character in self.active_chars if character.is_active]

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method on all active characters."""
        for character in self.active_chars:
            character.tick()
