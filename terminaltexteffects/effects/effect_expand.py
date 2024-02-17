import argparse

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils.terminal import Terminal
from terminaltexteffects.utils import graphics


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
        self.active_chars: list[EffectCharacter] = []
        self.gradient_stops: list[int | str] = self.args.gradient_stops

    def prepare_data(self) -> None:
        """Prepares the data for the effect by starting all of the characters from a point in the middle of the input data."""
        if len(self.gradient_stops) > 1:
            gradient = graphics.Gradient(self.gradient_stops, self.args.gradient_steps)

        for character in self.terminal._input_characters:
            character.motion.set_coordinate(self.terminal.output_area.center)
            input_coord_path = character.motion.new_path(
                speed=self.args.movement_speed,
                ease=self.args.easing,
            )
            input_coord_path.new_waypoint(character.input_coord)
            self.terminal.set_character_visibility(character, True)
            character.motion.activate_path(input_coord_path)
            self.active_chars.append(character)
            character.event_handler.register_event(
                EventHandler.Event.PATH_ACTIVATED, input_coord_path, EventHandler.Action.SET_LAYER, 1
            )
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE, input_coord_path, EventHandler.Action.SET_LAYER, 0
            )
            if self.gradient_stops:
                gradient_scn = character.animation.new_scene()
                if len(self.gradient_stops) > 1:
                    for step in gradient:
                        gradient_scn.add_frame(character.input_symbol, self.args.gradient_frames, color=step)
                else:
                    gradient_scn.add_frame(character.input_symbol, 1, color=self.gradient_stops[0])
                character.animation.activate_scene(gradient_scn)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        self.terminal.print()
        while self.active_chars:
            self.animate_chars()
            self.active_chars = [character for character in self.active_chars if character.is_active()]
            self.terminal.print()

    def animate_chars(self) -> None:
        for character in self.active_chars:
            character.tick()
