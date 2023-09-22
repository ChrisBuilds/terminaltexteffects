import argparse
import random

import terminaltexteffects.utils.argtypes as argtypes
import terminaltexteffects.utils.terminal as terminal
from terminaltexteffects import base_effect


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "scattered",
        formatter_class=argtypes.CustomFormatter,
        help="Move the characters into place from random starting locations.",
        description="scattered | Move the characters into place from random starting locations.",
        epilog=f"""{argtypes.EASING_EPILOG}
        
Example: terminaltexteffects scattered -a 0.01""",
    )
    effect_parser.set_defaults(effect_class=ScatteredEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.valid_animationrate,
        default=0.01,
        help="Time between animation steps.",
    )
    effect_parser.add_argument(
        "--movement-speed",
        type=argtypes.valid_speed,
        default=0.5,
        metavar="(float > 0)",
        help="Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )
    effect_parser.add_argument(
        "--easing",
        default="IN_OUT_BACK",
        type=argtypes.valid_ease,
        help="Easing function to use for character movement.",
    )


class ScatteredEffect(base_effect.Effect):
    """Effect that moves the characters into position from random starting locations."""

    def __init__(self, terminal: terminal.Terminal, args: argparse.Namespace):
        super().__init__(terminal, args)

    def prepare_data(self) -> None:
        """Prepares the data for the effect by scattering the characters within range of the input width and height."""
        for character in self.terminal.characters:
            if self.terminal.output_area.right < 2 or self.terminal.output_area.top < 2:
                character.motion.set_coordinate(1, 1)
            else:
                character.motion.set_coordinate(
                    random.randint(1, self.terminal.output_area.right - 1),
                    random.randint(1, self.terminal.output_area.top - 1),
                )
            character.motion.new_waypoint(
                "input_coord",
                character.input_coord.column,
                character.input_coord.row,
                speed=self.args.movement_speed,
                ease=self.args.easing,
            )
            character.motion.activate_waypoint("input_coord")
            character.is_active = True
            self.animating_chars.append(character)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        self.terminal.print()
        while self.pending_chars or self.animating_chars:
            self.animate_chars()
            self.animating_chars = [
                animating_char
                for animating_char in self.animating_chars
                if not animating_char.motion.movement_complete()
            ]
            self.terminal.print()

    def animate_chars(self) -> None:
        for animating_char in self.animating_chars:
            animating_char.motion.move()
