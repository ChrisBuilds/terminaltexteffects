import argparse
import random

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects import base_effect
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
        type=argtypes.valid_animationrate,
        default=0.003,
        help="Time to sleep between animation steps. Defaults to 0.01 seconds.",
    )
    effect_parser.add_argument(
        "--fade-startcolor",
        type=argtypes.valid_color,
        default="000000",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color to start the fade-in. Defaults to black.",
    )
    effect_parser.add_argument(
        "--fade-endcolor",
        type=argtypes.valid_color,
        default="ffffff",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color to fade towards. Defaults to white",
    )
    effect_parser.add_argument(
        "--fade-duration",
        type=argtypes.valid_duration,
        default=5,
        help="Duration the fade effect, in frames. Defaults to 5.",
    )


class RandomSequence(base_effect.Effect):
    """Prints the input data in a random sequence."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        """Initializes the effect.

        Args:
            terminal (Terminal): Terminal object.
            args (argparse.Namespace): Arguments from argparse.
        """
        super().__init__(terminal, args)
        self.fade_in = graphics.gradient(args.fade_startcolor, args.fade_endcolor, 10)

    def prepare_data(self) -> None:
        for character in self.terminal.characters:
            character.is_active = False
            for color in self.fade_in:
                character.animator.add_effect_to_scene("fade", character.input_symbol, color, self.args.fade_duration)
            character.animator.activate_scene("fade")
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
                animating_char
                for animating_char in self.animating_chars
                if not animating_char.animator.is_active_scene_complete()
            ]

    def animate_chars(self) -> None:
        """Animates the characters by calling the move method and step animation."""
        for animating_char in self.animating_chars:
            animating_char.animator.step_animation()
