"""Effect that pours the characters into position from the top, bottom, left, or right."""

import argparse
from enum import Enum, auto

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects import base_effect
from terminaltexteffects.utils.terminal import Terminal


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "pour",
        help="Pours the characters into position from the given direction.",
        description="pour | Pours the characters into position from the given direction.",
        epilog="Example: terminaltexteffects pour -a 0.004 --pour-direction down",
    )
    effect_parser.set_defaults(effect_class=PourEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.valid_animationrate,
        default=0.004,
        help="Time between animation steps. Defaults to 0.004 seconds.",
    )
    effect_parser.add_argument(
        "--pour-direction",
        default="down",
        choices=["up", "down", "left", "right"],
        help="Direction the text will pour. Defaults to down.",
    )
    effect_parser.add_argument(
        "--movement-speed",
        type=argtypes.valid_speed,
        default=0.2,
        metavar="(float > 0)",
        help="Movement speed of the characters. Defaults to 0.2. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )


class PourDirection(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()


class PourEffect(base_effect.Effect):
    """Effect that pours the characters into position from the top, bottom, left, or right."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        super().__init__(terminal, args)
        self.pour_direction = {
            "down": PourDirection.DOWN,
            "up": PourDirection.UP,
            "left": PourDirection.LEFT,
            "right": PourDirection.RIGHT,
        }.get(args.pour_direction, PourDirection.DOWN)

    def prepare_data(self) -> None:
        """Prepares the data for the effect by sorting the characters by the pour direction."""
        sort_map = {
            PourDirection.DOWN: lambda character: character.input_coord.row,
            PourDirection.UP: lambda character: -character.input_coord.row,
            PourDirection.LEFT: lambda character: character.input_coord.column,
            PourDirection.RIGHT: lambda character: -character.input_coord.column,
        }
        self.terminal.characters.sort(key=sort_map[self.pour_direction])
        for character in self.terminal.characters:
            character.is_active = False
            if self.pour_direction == PourDirection.DOWN:
                character.motion.set_coordinate(character.input_coord.column, self.terminal.output_area.top)
            elif self.pour_direction == PourDirection.UP:
                character.motion.set_coordinate(character.input_coord.column, self.terminal.output_area.bottom)
            elif self.pour_direction == PourDirection.LEFT:
                character.motion.set_coordinate(self.terminal.output_area.right, character.input_coord.row)
            elif self.pour_direction == PourDirection.RIGHT:
                character.motion.set_coordinate(self.terminal.output_area.left, character.input_coord.row)
            character.motion.new_waypoint(
                character.input_coord.column,
                character.input_coord.row,
                speed=self.args.movement_speed,
                ease=character.motion.ease.IN_SINE,
            )
            self.pending_chars.append(character)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        self.terminal.print()
        while self.pending_chars or self.animating_chars:
            if self.pending_chars:
                next_character = self.pending_chars.pop(0)
                next_character.is_active = True
                self.animating_chars.append(next_character)
            self.animate_chars()
            self.animating_chars = [
                animating_char
                for animating_char in self.animating_chars
                if not animating_char.motion.movement_complete()
            ]
            self.terminal.print()

    def animate_chars(self) -> None:
        """Animates the sliding characters."""
        for animating_char in self.animating_chars:
            animating_char.motion.move()
