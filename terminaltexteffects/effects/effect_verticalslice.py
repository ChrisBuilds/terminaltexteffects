import time
import argparse
import terminaltexteffects.utils.argtypes as argtypes
import terminaltexteffects.utils.terminaloperations as tops
from terminaltexteffects import base_effect


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "verticalslice",
        help="Slices the input in half vertically and slides it into place from opposite directions.",
        description="verticalslice | Slices the input in half vertically and slides it into place from opposite directions.",
        epilog="Example: terminaltexteffects verticalslice -a 0.02",
    )
    effect_parser.set_defaults(effect_class=VerticalSlice)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=float,
        default=0.02,
        help="Time between animation steps. Defaults to 0.02 seconds.",
    )


class VerticalSlice(base_effect.Effect):
    """Effect that slices the input in half vertically and slides it into place from opposite directions."""

    def __init__(self, input_data: str, args: argparse.Namespace):
        super().__init__(input_data, args.animation_rate)

    def prepare_data(self) -> None:
        """Prepares the data for the effect by setting the left half to start at the top and the
        right half to start at the bottom, and creating rows consisting off halves from opposite
        input rows."""

        self.rows = list(self.input_by_row().values())
        lengths = [max([c.input_coord.column for c in row]) for row in self.rows]
        mid_point = sum(lengths) // len(lengths) // 2
        self.new_rows = []
        for i, row in enumerate(self.rows):
            new_row = []
            left_half = [c for c in row if c.input_coord.column <= mid_point]
            for c in left_half:
                c.current_coord.row = self.output_area.top
            opposite_row = self.rows[-(i + 1)]
            right_half = [c for c in opposite_row if c.input_coord.column > mid_point]
            for c in right_half:
                c.current_coord.row = self.output_area.bottom
            new_row.extend(left_half)
            new_row.extend(right_half)
            self.new_rows.append(new_row)

    def run(self) -> None:
        """Runs the effect."""
        self.prep_terminal()
        self.prepare_data()
        while self.new_rows or self.animating_chars:
            if self.new_rows:
                self.animating_chars.extend(self.new_rows.pop(0))
            self.animate_chars()

            # remove completed chars from animating chars
            self.animating_chars = [
                animating_char for animating_char in self.animating_chars if not animating_char.animation_completed()
            ]

    def animate_chars(self) -> None:
        """Animates the characters by calling the move method and printing the characters to the terminal."""
        for animating_char in self.animating_chars:
            tops.print_character(animating_char, clear_last=True)
            animating_char.move()
        time.sleep(self.animation_rate)
