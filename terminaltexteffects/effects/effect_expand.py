import argparse

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils.terminal import Terminal


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "expand",
        formatter_class=argtypes.CustomFormatter,
        help="Expands the text from a single point.",
        description="expand | Expands the text from a single point.",
        epilog=f"""{argtypes.EASING_EPILOG}
        
Example: terminaltexteffects expand -a 0.01""",
    )
    effect_parser.set_defaults(effect_class=ExpandEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.valid_animationrate,
        default=0.01,
        help="Time, in seconds, between animation steps.",
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
        default="IN_OUT_QUART",
        type=argtypes.valid_ease,
        help="Easing function to use for character movement.",
    )


class ExpandEffect:
    """Effect that draws the characters expanding from a single point."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.animating_chars: list[EffectCharacter] = []

    def prepare_data(self) -> None:
        """Prepares the data for the effect by starting all of the characters from a point in the middle of the input data."""

        for character in self.terminal.characters:
            character.motion.set_coordinate(self.terminal.output_area.center)
            input_coord_wpt = character.motion.new_waypoint(
                "input_coord",
                character.input_coord,
                speed=self.args.movement_speed,
                ease=self.args.easing,
            )
            character.is_active = True
            character.motion.activate_waypoint(input_coord_wpt)
            self.animating_chars.append(character)
            character.event_handler.register_event(
                EventHandler.Event.WAYPOINT_ACTIVATED, input_coord_wpt, EventHandler.Action.SET_LAYER, 1
            )
            character.event_handler.register_event(
                EventHandler.Event.WAYPOINT_REACHED, input_coord_wpt, EventHandler.Action.SET_LAYER, 0
            )

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        self.terminal.print()
        while self.animating_chars:
            self.animate_chars()
            self.animating_chars = [
                animating for animating in self.animating_chars if not animating.motion.movement_is_complete()
            ]
            self.terminal.print()

    def animate_chars(self) -> None:
        for animating_char in self.animating_chars:
            animating_char.motion.move()
