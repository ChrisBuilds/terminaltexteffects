import argparse

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils import geometry, graphics
from terminaltexteffects.utils.terminal import Terminal


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "slide",
        formatter_class=argtypes.CustomFormatter,
        help="Slide characters into view from outside the terminal.",
        description="Slide characters into view from outside the terminal, grouped by row, column, or diagonal.",
        epilog=f"""{argtypes.EASING_EPILOG}

Example: terminaltexteffects slide --grouping row --movement-speed 0.5 --gradient 10 11 12 13 14 --gap 5 --merge --gradient-steps 10 --easing OUT_QUAD""",
    )
    effect_parser.set_defaults(effect_class=SlideEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.nonnegative_float,
        default=0.01,
        help="Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have no impact beyond a certain lower threshold due to the processing speed of your device.",
    )
    effect_parser.add_argument(
        "--movement-speed",
        type=argtypes.positive_float,
        default=0.5,
        metavar="(float > 0)",
        help="Speed of the characters.",
    )
    effect_parser.add_argument(
        "--grouping",
        default="row",
        choices=[
            "row",
            "column",
            "diagonal",
        ],
        help="Direction to group characters.",
    )
    effect_parser.add_argument(
        "--gradient-stops",
        type=argtypes.color,
        nargs="+",
        default=["8A008A", "00D1FF", "FFFFFF"],
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the character gradient. If only one color is provided, the characters will be displayed in that color.",
    )
    effect_parser.add_argument(
        "--gradient-steps",
        type=argtypes.positive_int,
        default=[12],
        nargs="+",
        metavar="(int > 0)",
        help="Number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )
    effect_parser.add_argument(
        "--gradient-frames",
        type=argtypes.positive_int,
        default=10,
        metavar="(int > 0)",
        help="Number of frames to display each gradient step.",
    )
    effect_parser.add_argument(
        "--gradient-direction",
        default="vertical",
        type=argtypes.gradient_direction,
        help="Direction of the gradient (vertical, horizontal, diagonal, center).",
    )
    effect_parser.add_argument(
        "--gap",
        type=argtypes.nonnegative_int,
        default=3,
        metavar="(int >= 0)",
        help="Number of frames to wait before adding the next group of characters. Increasing this value creates a more staggered effect.",
    )
    effect_parser.add_argument(
        "--reverse-direction",
        action="store_true",
        help="Reverse the direction of the characters.",
    )
    effect_parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge the character groups originating from either side of the terminal. (--reverse-direction is ignored when merging)",
    )
    effect_parser.add_argument(
        "--easing",
        default="OUT_QUAD",
        type=argtypes.ease,
        help="Easing function to use for character movement.",
    )


class SlideEffect:
    """Effect that slides characters into view from outside the terminal. Characters are grouped by column, row, or diagonal."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.grouping: str = self.args.grouping
        self.reverse_direction: bool = self.args.reverse_direction
        self.merge: bool = self.args.merge
        self.gradient_stops: list[int | str] = self.args.gradient_stops
        self.gap = self.args.gap
        self.pending_groups: list[list[EffectCharacter]] = []
        self.easing = self.args.easing
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_data(self) -> None:
        """Prepares the data for the effect by setting starting coordinates and building Paths/Scenes."""
        final_gradient = graphics.Gradient(self.args.gradient_stops, self.args.gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.args.gradient_direction
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
                    [self.gradient_stops[0], self.character_final_color_map[character]], 10
                )
                gradient_scn.apply_gradient_to_symbols(char_gradient, character.input_symbol, self.args.gradient_frames)
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
