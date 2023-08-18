"""Creates a rain effect where characters fall from the top of the terminal."""

import time
import random
import argparse
import terminaltexteffects.utils.argtypes as argtypes
import terminaltexteffects.utils.terminaloperations as tops
from terminaltexteffects import base_effect, base_character


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "rain",
        help="Rain characters from the top of the output area.",
        description="rain | Rain characters from the top of the output area.",
        epilog="Example: terminaltexteffects rain -a 0.004 --rain-color 40",
    )
    effect_parser.set_defaults(effect_class=RainEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=float,
        default=0.01,
        help="Time between animation steps. Defaults to 0.01 seconds.",
    )


class RainEffect(base_effect.Effect):
    """Creates a rain effect where characters fall from the top of the output area."""

    def __init__(self, input_data: str, args: argparse.Namespace):
        super().__init__(input_data, args.animation_rate)
        self.group_by_row: dict[int, list[base_character.EffectCharacter | None]] = {}

    def prepare_data(self) -> None:
        """Prepares the data for the effect by setting all characters y position to the input height and sorting by target y."""

        for character in self.characters:
            character.current_coord.column = character.input_coord.column
            character.current_coord.row = min(self.input_height, self.terminal_height - 1)
            self.pending_chars.append(character)
        for character in sorted(self.pending_chars, key=lambda c: c.input_coord.row):
            if character.input_coord.row not in self.group_by_row:
                self.group_by_row[character.input_coord.row] = []
            self.group_by_row[character.input_coord.row].append(character)

    def run(self) -> None:
        """Runs the effect."""
        self.prep_terminal()
        self.prepare_data()
        self.pending_chars.clear()
        while self.group_by_row or self.animating_chars or self.pending_chars:
            if not self.pending_chars and self.group_by_row:
                self.pending_chars.extend(self.group_by_row.pop(min(self.group_by_row.keys())))  # type: ignore
            if self.pending_chars:
                for _ in range(random.randint(1, 3)):
                    if self.pending_chars:
                        self.animating_chars.append(
                            self.pending_chars.pop(random.randint(0, len(self.pending_chars) - 1))
                        )
                    else:
                        break
            self.animate_chars()
            # remove completed chars from animating chars
            self.animating_chars = [
                animating_char for animating_char in self.animating_chars if not animating_char.animation_completed()
            ]

    def animate_chars(self) -> None:
        """Animates the characters by calling the tween method and printing the characters to the terminal."""
        for animating_char in self.animating_chars:
            # disable all graphical modes if the character is at the final position
            if animating_char.current_coord == animating_char.input_coord:
                animating_char.graphical_effect.disable_modes()
            tops.print_character(animating_char, True)
            animating_char.move()
            animating_char.step_animation()
        time.sleep(self.animation_rate)
