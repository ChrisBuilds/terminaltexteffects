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
        
Example: terminaltexteffects expand -a 0.01 --movement-speed 0.5 --easing IN_OUT_QUART""",
    )
    effect_parser.set_defaults(effect_class=ExpandEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.nonnegative_float,
        default=0.01,
        help="Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have no impact beyond a certain lower threshold due to the processing speed of your device.",
    )
    effect_parser.add_argument(
        "--movement-speed",
        type=argtypes.positive_float,
        default=0.5,
        metavar="(float > 0)",
        help="Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )
    effect_parser.add_argument(
        "--easing",
        default="IN_OUT_QUART",
        type=argtypes.ease,
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
            input_coord_path = character.motion.new_path(
                "input_coord",
                speed=self.args.movement_speed,
                ease=self.args.easing,
            )
            input_coord_wpt = input_coord_path.new_waypoint("input_coord", character.input_coord)
            character.is_active = True
            character.motion.activate_path(input_coord_path)
            self.animating_chars.append(character)
            character.event_handler.register_event(
                EventHandler.Event.PATH_ACTIVATED, input_coord_path, EventHandler.Action.SET_LAYER, 1
            )
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE, input_coord_path, EventHandler.Action.SET_LAYER, 0
            )

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        self.terminal.print()
        while self.animating_chars:
            self.animate_chars()
            self.animating_chars = [
                animating_char for animating_char in self.animating_chars if animating_char.is_animating()
            ]
            self.terminal.print()

    def animate_chars(self) -> None:
        for animating_char in self.animating_chars:
            animating_char.tick()
