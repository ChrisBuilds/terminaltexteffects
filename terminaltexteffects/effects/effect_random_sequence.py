import argparse
import random
import time

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects import base_effect
from terminaltexteffects.utils.terminal import Terminal


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
        default=0.003,
        help="Time to sleep between animation steps. Defaults to 0.01 seconds.",
    )


class RandomSequence(base_effect.Effect):
    """Prints the input data in a random sequence."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        """Initializes the effect.

        Args:
            terminal (Terminal): Terminal object.
            args (argparse.Namespace): Arguments from argparse.
        """
        super().__init__(terminal, args.animation_rate)

    def prepare_data(self) -> None:
        for character in self.terminal.characters:
            character.is_active = False

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        random.shuffle(self.terminal.characters)
        for character in self.terminal.characters:
            character.is_active = True
            self.terminal.print()
            time.sleep(self.animation_rate)
