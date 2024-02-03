import argparse

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils.terminal import Terminal
from terminaltexteffects.utils import graphics, argtypes, motion


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "middleout",
        formatter_class=argtypes.CustomFormatter,
        help="Text expands in a single row or column in the middle of the output area then out.",
        description="Text expands in a single row or column in the middle of the output area then out.",
        epilog=f"""{argtypes.EASING_EPILOG}

Example: terminaltexteffects middleout -a 0.01 --expand-direction horizontal --center-movement-speed 0.35 
         --full-movement-speed 0.35 --center-easing IN_OUT_SINE --full-easing IN_OUT_SINE 
         --center-expand-color 00ff00 --full-expand-color 0000ff --starting-color ff0000""",
    )
    effect_parser.set_defaults(effect_class=MiddleoutEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.nonnegative_float,
        default=0.01,
        help="Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have no impact beyond a certain lower threshold due to the processing speed of your device.",
    )
    effect_parser.add_argument(
        "--starting-color",
        type=argtypes.color,
        default="ffffff",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the initial text in the center of the output area.",
    )
    effect_parser.add_argument(
        "--center-expand-color",
        type=argtypes.color,
        default="ffffff",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the row or column as it expands.",
    )
    effect_parser.add_argument(
        "--full-expand-color",
        type=argtypes.color,
        default="ffffff",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the full text as it expands.",
    )
    effect_parser.add_argument(
        "--expand-direction",
        default="vertical",
        choices=["vertical", "horizontal"],
        help="Direction the text will expand.",
    )
    effect_parser.add_argument(
        "--center-movement-speed",
        type=argtypes.positive_float,
        default=0.35,
        metavar="(float > 0)",
        help="Speed of the characters during the initial expansion of the center vertical/horiztonal line. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )
    effect_parser.add_argument(
        "--full-movement-speed",
        type=argtypes.positive_float,
        default=0.35,
        metavar="(float > 0)",
        help="Speed of the characters during the final full expansion. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )
    effect_parser.add_argument(
        "--center-easing",
        default="IN_OUT_SINE",
        type=argtypes.ease,
        help="Easing function to use for initial expansion.",
    )
    effect_parser.add_argument(
        "--full-easing",
        default="IN_OUT_SINE",
        type=argtypes.ease,
        help="Easing function to use for full expansion.",
    )


class MiddleoutEffect:
    """Effect that expands a single row and column followed by the rest of the output area."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.animating_chars: list[EffectCharacter] = []
        self.center_gradient = graphics.Gradient([self.args.starting_color, self.args.center_expand_color], 10)
        self.full_gradient = graphics.Gradient([self.args.center_expand_color, self.args.full_expand_color], 10)

    def prepare_data(self) -> None:
        """Prepares the data for the effect."""
        for character in self.terminal.characters:
            character.motion.set_coordinate(self.terminal.output_area.center)
            # setup waypoints
            if self.args.expand_direction == "vertical":
                column = character.input_coord.column
                row = self.terminal.output_area.center_row
            else:
                column = self.terminal.output_area.center_column
                row = character.input_coord.row
            center_path = character.motion.new_path(
                "center", speed=self.args.center_movement_speed, ease=self.args.center_easing
            )
            center_waypoint = center_path.new_waypoint("center", motion.Coord(column, row))
            full_path = character.motion.new_path(
                "full", speed=self.args.full_movement_speed, ease=self.args.full_easing
            )
            full_waypoint = full_path.new_waypoint("full", character.input_coord)

            # setup scenes
            center_scene = character.animation.new_scene("center")
            full_scene = character.animation.new_scene("full")
            for step in self.center_gradient:
                center_scene.add_frame(character.input_symbol, 2, color=step)
            for step in self.full_gradient:
                full_scene.add_frame(character.input_symbol, 2, color=step)
            character.animation.activate_scene(center_scene)

            # initialize character state
            character.motion.activate_path(center_path)
            character.animation.activate_scene(center_scene)
            character.is_active = True
            self.animating_chars.append(character)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        final = False
        while self.pending_chars or self.animating_chars:
            if all([character.motion.active_path is None for character in self.animating_chars]):
                final = True
                for character in self.animating_chars:
                    character.motion.activate_path(character.motion.paths["full"])
                    character.animation.activate_scene(character.animation.scenes["full"])
            self.terminal.print()
            self.animate_chars()
            if final:
                self.animating_chars = [
                    animating_char for animating_char in self.animating_chars if animating_char.is_animating()
                ]

    def animate_chars(self) -> None:
        """Animates the characters by calling the move method and step animation."""
        for animating_char in self.animating_chars:
            animating_char.tick()
