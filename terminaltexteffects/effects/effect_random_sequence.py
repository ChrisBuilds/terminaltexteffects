import random
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
        "randomsequence",
        help="Prints the input data in a random sequence.",
        description="randomsequence | Prints the input data in a random sequence.",
        epilog="Example: terminaltexteffects randomsequence -a 0.01",
    )
    effect_parser.set_defaults(effect_class=RandomSequence)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=float,
        default=0.01,
        help="Time to sleep between animation steps. Defaults to 0.01 seconds.",
    )


class RandomSequence(base_effect.Effect):
    """Prints the input data in a random sequence."""

    def __init__(self, input_data: str, args: argparse.Namespace):
        """Initializes the effect.

        Args:
            input_data (str): The input data.
            args (argparse.Namespace): Arguments from argparse.
        """
        super().__init__(input_data, args.animation_rate)

    def run(self) -> None:
        """Runs the effect."""
        self.prep_terminal()
        random.shuffle(self.characters)
        for character in self.characters:
            tops.print_character(character)
            time.sleep(self.animation_rate)
