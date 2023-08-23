import time
import argparse
from terminaltexteffects.utils.terminal import Terminal
import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects import base_effect, base_character


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "effect_name", help="effect_description", description="effect_description", epilog="Example: effect_example"
    )
    effect_parser.set_defaults(effect_class=NamedEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=float,
        default=0.01,
        help="Time between animation steps. Defaults to 0.01 seconds.",
    )
    effect_parser.add_argument(
        "--color-description",
        type=argtypes.color_range,
        default=0,
        metavar="[0-255]",
        help="Xterm color code for the ___. Defaults to 0",
    )


class NamedEffect(base_effect.Effect):
    """Effect that ___."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        super().__init__(terminal, args.animation_rate)

    def prepare_data(self) -> None:
        """Prepares the data for the effect by ___."""

        for character in self.terminal.characters:
            pass
            # do something with the data if needed (sort, adjust positions, etc)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        while self.pending_chars or self.animating_chars:
            self.terminal.print()
            self.animate_chars()

            # remove completed chars from animating chars
            self.animating_chars = [
                animating_char
                for animating_char in self.animating_chars
                if not animating_char.animator.is_active_scene_complete()
                or animating_char.current_coord != animating_char.input_coord
            ]
            time.sleep(self.animation_rate)

    def animate_chars(self) -> None:
        """Animates the characters by calling the move method and step animation."""
        for animating_char in self.animating_chars:
            animating_char.animator.step_animation()
            animating_char.move()
            if animating_char.is_movement_complete():
                animating_char.symbol = animating_char.input_symbol
