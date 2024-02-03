import argparse
import random

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils.terminal import Terminal
from terminaltexteffects.utils import graphics


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
        type=argtypes.nonnegative_float,
        default=0.003,
        help="Time to sleep between animation steps. Defaults to 0.01 seconds.",
    )
    effect_parser.add_argument(
        "--gradient-stops",
        type=argtypes.color,
        nargs="*",
        default=[],
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the character gradient. If only one color is provided, the characters will be displayed in that color.",
    )
    effect_parser.add_argument(
        "--gradient-steps",
        type=argtypes.positive_int,
        default=10,
        metavar="(int > 0)",
        help="Number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )
    effect_parser.add_argument(
        "--gradient-frames",
        type=argtypes.positive_int,
        default=5,
        metavar="(int > 0)",
        help="Number of frames to display each gradient step.",
    )


class RandomSequence:
    """Prints the input data in a random sequence."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        """Initializes the effect.

        Args:
            terminal (Terminal): Terminal object.
            args (argparse.Namespace): Arguments from argparse.
        """
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.animating_chars: list[EffectCharacter] = []
        self.gradient_stops: list[int | str] = self.args.gradient_stops

    def prepare_data(self) -> None:
        if len(self.gradient_stops) > 1:
            gradient = graphics.Gradient(self.gradient_stops, self.args.gradient_steps)
        for character in self.terminal.characters:
            character.is_active = False
            if self.gradient_stops:
                gradient_scn = character.animation.new_scene("gradient_scn")
                if len(self.gradient_stops) > 1:
                    for step in gradient:
                        gradient_scn.add_frame(character.input_symbol, self.args.gradient_frames, color=step)
                else:
                    gradient_scn.add_frame(character.input_symbol, 1, color=self.gradient_stops[0])
                character.animation.activate_scene(gradient_scn)
            self.pending_chars.append(character)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()

        random.shuffle(self.pending_chars)
        while self.pending_chars or self.animating_chars:
            if self.pending_chars:
                self.next_char = self.pending_chars.pop()
                self.next_char.is_active = True
                self.animating_chars.append(self.next_char)
            self.animate_chars()
            self.terminal.print()
            # remove completed chars from animating chars
            self.animating_chars = [
                animating_char for animating_char in self.animating_chars if animating_char.is_animating()
            ]

    def animate_chars(self) -> None:
        """Animates the characters by calling the move method and step animation."""
        for animating_char in self.animating_chars:
            animating_char.tick()
