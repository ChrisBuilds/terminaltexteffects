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
        "rowmerge",
        help="Merges rows of characters.",
        description="rowmerge | Merges rows of characters.",
        epilog="Example: terminaltexteffects rowmerge -a 0.03",
    )
    effect_parser.set_defaults(effect_class=RowMergeEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=float,
        default=0.01,
        help="Time to sleep between animation steps. Defaults to 0.03 seconds.",
    )


class RowMergeEffect(base_effect.Effect):
    """Effect that merges rows."""

    def __init__(self, input_data: str, args: argparse.Namespace):
        super().__init__(input_data, args.animation_rate)

    def prepare_data(self) -> None:
        """Prepares the data for the effect by setting every other row to start at the opposite
        side of the terminal and reverse the order."""

        self.rows = []
        for i, row in self.input_by_row().items():
            if i % 2 == 0:
                row = row[::-1]
                for c in row:
                    c.current_coord.column = self.output_area.left
            else:
                for c in row:
                    c.current_coord.column = self.output_area.right
            self.rows.append(row)

    def run(self) -> None:
        """Runs the effect."""
        self.prep_terminal()
        self.prepare_data()
        while self.rows or self.animating_chars:
            self.animate_chars()
            for row in self.rows:
                if row:
                    self.animating_chars.append(row.pop(0))
            self.rows = [row for row in self.rows if row]

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
