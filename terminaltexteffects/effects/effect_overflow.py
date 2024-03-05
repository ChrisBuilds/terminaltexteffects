import argparse
import random

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils import graphics
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "overflow",
        formatter_class=argtypes.CustomFormatter,
        help="Input text overflows ands scrolls the terminal in a random order until eventually appearing ordered.",
        description="Input text overflows ands scrolls the terminal in a random order until eventually appearing ordered.",
        epilog="""Example: terminaltexteffects overflow --final-color f3b462 --overflow-gradient-stops f2ebc0 8dbfb3 f2ebc0 --overflow-cycles-range 2-4 --overflow-speed 3""",
    )
    effect_parser.set_defaults(effect_class=OverflowEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.nonnegative_float,
        default=0.01,
        help="Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have no impact beyond a certain lower threshold due to the processing speed of your device.",
    )
    effect_parser.add_argument(
        "--final-gradient-stops",
        type=argtypes.color,
        nargs="+",
        default=["8A008A", "00D1FF", "FFFFFF"],
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )
    effect_parser.add_argument(
        "--final-gradient-steps",
        type=argtypes.positive_int,
        nargs="+",
        default=[12],
        metavar="(int > 0)",
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )
    effect_parser.add_argument(
        "--overflow-gradient-stops",
        type=argtypes.color,
        nargs="+",
        default=["f2ebc0", "8dbfb3", "f2ebc0"],
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the overflow gradient.",
    )
    effect_parser.add_argument(
        "--overflow-cycles-range",
        type=argtypes.int_range,
        default="2-4",
        metavar="(min-max)",
        help="Number of cycles to overflow the text.",
    )
    effect_parser.add_argument(
        "--overflow-speed",
        type=argtypes.positive_int,
        default=3,
        metavar="int > 0",
        help="Speed of the overflow effect.",
    )


class Row:
    def __init__(self, characters: list[EffectCharacter], final: bool = False) -> None:
        self.characters = characters
        self.current_index = 0
        self.final = final

    def move_up(self) -> None:
        for character in self.characters:
            current_row = character.motion.current_coord.row
            character.motion.set_coordinate(Coord(character.motion.current_coord.column, current_row + 1))

    def setup(self) -> None:
        for character in self.characters:
            character.motion.set_coordinate(Coord(character.input_coord.column, 0))

    def set_color(self, color: int | str) -> None:
        for character in self.characters:
            character.animation.set_appearance(character.input_symbol, color)


class OverflowEffect:
    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.pending_rows: list[Row] = []
        self.active_rows: list[Row] = []

    def prepare_data(self) -> None:
        """Prepares the data for the effect by ___."""
        final_gradient = graphics.Gradient(self.args.final_gradient_stops, self.args.final_gradient_steps)

        lower_range, upper_range = self.args.overflow_cycles_range
        rows = self.terminal.get_characters_grouped(Terminal.CharacterGroup.ROW_TOP_TO_BOTTOM)
        if upper_range > 0:
            for _ in range(random.randint(lower_range, upper_range)):
                random.shuffle(rows)
                for row in rows:
                    copied_characters = [
                        self.terminal.add_character(character.input_symbol, character.input_coord) for character in row
                    ]
                    self.pending_rows.append(Row(copied_characters))
        # add rows in correct order to the end of self.pending_rows
        for row in self.terminal.get_characters_grouped(Terminal.CharacterGroup.ROW_TOP_TO_BOTTOM, fill_chars=True):
            next_row = Row(row)
            next_row.set_color(
                final_gradient.get_color_at_fraction(row[0].input_coord.row / self.terminal.output_area.top)
            )
            self.pending_rows.append(Row(row, final=True))

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        delay = 0
        g = graphics.Gradient(
            self.args.overflow_gradient_stops,
            max((self.terminal.output_area.top // max(1, len(self.args.overflow_gradient_stops) - 1)), 1),
        )

        while self.pending_rows:
            if not delay:
                for _ in range(random.randint(1, self.args.overflow_speed)):
                    if self.pending_rows:
                        for row in self.active_rows:
                            row.move_up()
                            if not row.final:
                                row.set_color(
                                    g.spectrum[min(row.characters[0].motion.current_coord.row, len(g.spectrum) - 1)]
                                )
                        next_row = self.pending_rows.pop(0)
                        next_row.setup()
                        next_row.move_up()
                        if not next_row.final:
                            next_row.set_color(g.spectrum[0])
                        for character in next_row.characters:
                            self.terminal.set_character_visibility(character, True)
                        self.active_rows.append(next_row)
                delay = random.randint(0, 3)

            else:
                delay -= 1
            self.active_rows = [
                row
                for row in self.active_rows
                if row.characters[0].motion.current_coord.row <= self.terminal.output_area.top
            ]
            self.terminal.print()
            self.animate_chars()

            self.active_chars = [character for character in self.active_chars if character.is_active]

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method on all active characters."""
        for character in self.active_chars:
            character.tick()
