import argparse
import random

import terminaltexteffects.utils.argtypes as argtypes
import terminaltexteffects.utils.graphics as graphics
from terminaltexteffects import base_character, base_effect
from terminaltexteffects.utils.terminal import Terminal


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "shootingstar",
        help="Displays the text as a falling star toward the final coordinate of the character.",
        description="shootingstar | Displays the text as a falling star toward the final coordinate of the character.",
        epilog="Example: terminaltexteffects shootingstar -a 0.01",
    )
    effect_parser.set_defaults(effect_class=ShootingStarEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=float,
        default=0.01,
        help="Time between animation steps. Defaults to 0.01 seconds.",
    )


class ShootingStarEffect(base_effect.Effect):
    """Effect that display the text as a falling star toward the final coordinate of the character."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        super().__init__(terminal)
        self.group_by_row: dict[int, list[base_character.EffectCharacter | None]] = {}

    def prepare_data(self) -> None:
        """Prepares the data for the effect by sorting by row and assigning the star symbol."""

        for character in self.terminal.characters:
            character.is_active = False
            character.animator.add_effect_to_scene("star", "*", random.randint(1, 10), 1)
            character.animator.active_scene_name = "star"
            character.current_coord = base_character.Coord(self.random_column(), self.terminal.output_area.top)
            self.pending_chars.append(character)
        for character in sorted(self.pending_chars, key=lambda c: c.input_coord.row):
            if character.input_coord.row not in self.group_by_row:
                self.group_by_row[character.input_coord.row] = []
            self.group_by_row[character.input_coord.row].append(character)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        self.pending_chars.clear()
        while self.group_by_row or self.animating_chars or self.pending_chars:
            if not self.pending_chars and self.group_by_row:
                self.pending_chars.extend(self.group_by_row.pop(min(self.group_by_row.keys())))  # type: ignore
            if self.pending_chars:
                for _ in range(random.randint(1, 3)):
                    if self.pending_chars:
                        next_character = self.pending_chars.pop(random.randint(0, len(self.pending_chars) - 1))
                        next_character.is_active = True
                        self.animating_chars.append(next_character)
                    else:
                        break
            self.animate_chars()
            self.animating_chars = [
                animating_char
                for animating_char in self.animating_chars
                if not animating_char.animator.is_active_scene_complete() or not animating_char.is_movement_complete()
            ]
            self.terminal.print()

    def animate_chars(self) -> None:
        """Animates the characters by calling the tween method and printing the characters to the terminal."""
        for animating_char in self.animating_chars:
            animating_char.animator.step_animation()
            animating_char.move()
            if animating_char.is_movement_complete():
                animating_char.symbol = animating_char.input_symbol
