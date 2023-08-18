import time
import argparse
import terminaltexteffects.utils.terminaloperations as tops
import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects import base_effect, base_character


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser("effect_name", help="effect_description")
    effect_parser.set_defaults(effect_class=NamedEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=float,
        default=0.01,
        help="Time to sleep between animation steps. Defaults to 0.01 seconds.",
    )
    effect_parser.add_argument(
        "--color-description",
        type=argtypes.color_range,
        default=0,
        metavar="[0-255]",
        help="Xterm color code for the ___. Defaults to 0",
    )


class NamedEffect(base_effect.Effect):
    """Effect that ___."""

    def __init__(self, input_data: str, args: argparse.Namespace):
        super().__init__(input_data, args.animation_rate)

    def prepare_data(self) -> None:
        """Prepares the data for the effect by ___."""

        for character in self.characters:
            pass
            # do something with the data if needed (sort, adjust positions, etc)

    def run(self) -> None:
        """Runs the effect."""
        self.prep_terminal()
        self.prepare_data()
        while self.pending_chars or self.animating_chars:
            self.animate_chars()

            # tracking completed chars (remove if unnecessary)
            self.completed_chars.extend(
                [animating_char for animating_char in self.animating_chars if animating_char.animation_completed()]
            )
            self.maintain_completed()

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
