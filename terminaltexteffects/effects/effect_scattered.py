import time
import argparse
import terminaltexteffects.utils.argtypes as argtypes
import terminaltexteffects.utils.terminaloperations as tops
from terminaltexteffects import base_effect
import random


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "scattered",
        help="Move the characters into place from random starting locations.",
        description="scattered | Move the characters into place from random starting locations.",
        epilog="Example: terminaltexteffects scattered -a 0.01",
    )
    effect_parser.set_defaults(effect_class=ScatteredEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=float,
        default=0.01,
        help="Time between animation steps. Defaults to 0.01 seconds.",
    )


class ScatteredEffect(base_effect.Effect):
    """Effect that moves the characters into position from random starting locations."""

    def __init__(self, input_data: str, args: argparse.Namespace):
        super().__init__(input_data, args.animation_rate)

    def prepare_data(self) -> None:
        """Prepares the data for the effect by scattering the characters within range of the input width and height."""
        for character in self.characters:
            character.current_coord.column = random.randint(1, self.output_area.right - 1)
            character.current_coord.row = random.randint(1, self.output_area.top - 1)
            character.graphical_effect.dim = True
            self.animating_chars.append(character)

    def run(self) -> None:
        """Runs the effect."""
        self.prep_terminal()
        self.prepare_data()
        while self.pending_chars or self.animating_chars:
            self.animate_chars()
            self.completed_chars.extend(
                [completed_char for completed_char in self.animating_chars if completed_char.animation_completed()]
            )
            self.maintain_completed()
            self.animating_chars = [
                animating_char for animating_char in self.animating_chars if not animating_char.animation_completed()
            ]

    def animate_chars(self) -> None:
        for animating_char in self.animating_chars:
            if animating_char.current_coord == animating_char.input_coord:
                animating_char.graphical_effect.disable_modes()
            tops.print_character(animating_char, clear_last=True)
            animating_char.move()
        time.sleep(self.animation_rate)
