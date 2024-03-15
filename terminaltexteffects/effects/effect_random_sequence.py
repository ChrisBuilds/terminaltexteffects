import argparse
import random

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils import graphics
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
        epilog="Example: terminaltexteffects randomsequence --starting-color 8A008A --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --final-gradient-frames 12 --speed 0.0001",
    )
    effect_parser.set_defaults(effect_class=RandomSequence)
    effect_parser.add_argument(
        "--starting-color",
        type=argtypes.color,
        default="000000",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color of the characters at spawn.",
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
        "--final-gradient-frames",
        type=argtypes.positive_int,
        default=12,
        metavar="(int > 0)",
        help="Number of frames to display each gradient step.",
    )
    effect_parser.add_argument(
        "--speed",
        type=argtypes.positive_float,
        default=0.0001,
        metavar="(float > 0)",
        help="Speed of the animation as a percentage of the total number of characters. Defaults to 0.0001.",
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
        self.active_chars: list[EffectCharacter] = []
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_data(self) -> None:
        final_gradient = graphics.Gradient(self.args.final_gradient_stops, self.args.final_gradient_steps)

        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient.get_color_at_fraction(
                character.input_coord.row / self.terminal.output_area.top
            )

        for character in self.terminal.get_characters():
            self.terminal.set_character_visibility(character, False)
            gradient_scn = character.animation.new_scene()
            gradient = graphics.Gradient([self.args.starting_color, self.character_final_color_map[character]], 7)
            gradient_scn.apply_gradient_to_symbols(gradient, character.input_symbol, self.args.final_gradient_frames)
            character.animation.activate_scene(gradient_scn)
            self.pending_chars.append(character)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        random.shuffle(self.pending_chars)
        characters_per_tick = max(int(self.args.speed * len(self.terminal._input_characters)), 1)
        while self.pending_chars or self.active_chars:
            for _ in range(characters_per_tick):
                if self.pending_chars:
                    self.next_char = self.pending_chars.pop()
                    self.terminal.set_character_visibility(self.next_char, True)
                    self.active_chars.append(self.next_char)
            self.animate_chars()
            self.terminal.print()
            self.active_chars = [character for character in self.active_chars if character.is_active]

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method."""
        for character in self.active_chars:
            character.tick()
