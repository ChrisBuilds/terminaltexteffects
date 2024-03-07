import argparse

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils import graphics
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal


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
    """Effect that expands a single row and column followed by the rest of the output area"""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_data(self) -> None:
        """Prepares the data for the effect."""
        final_gradient = graphics.Gradient(self.args.final_gradient_stops, self.args.final_gradient_steps)

        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient.get_color_at_fraction(
                character.input_coord.row / self.terminal.output_area.top
            )

            character.motion.set_coordinate(self.terminal.output_area.center)
            # setup waypoints
            if self.args.expand_direction == "vertical":
                column = character.input_coord.column
                row = self.terminal.output_area.center_row
            else:
                column = self.terminal.output_area.center_column
                row = character.input_coord.row
            center_path = character.motion.new_path(speed=self.args.center_movement_speed, ease=self.args.center_easing)
            center_path.new_waypoint(Coord(column, row))
            full_path = character.motion.new_path(
                id="full", speed=self.args.full_movement_speed, ease=self.args.full_easing
            )
            full_path.new_waypoint(character.input_coord, id="full")

            # setup scenes
            full_scene = character.animation.new_scene(id="full")
            full_gradient = graphics.Gradient([self.args.starting_color, self.character_final_color_map[character]], 10)
            full_scene.apply_gradient_to_symbols(full_gradient, character.input_symbol, 10)

            # initialize character state
            character.motion.activate_path(center_path)
            character.animation.set_appearance(character.input_symbol, self.args.starting_color)
            self.terminal.set_character_visibility(character, True)
            self.active_chars.append(character)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        final = False
        while self.pending_chars or self.active_chars:
            if all([character.motion.active_path is None for character in self.active_chars]):
                final = True
                for character in self.active_chars:
                    character.motion.activate_path(character.motion.query_path("full"))
                    character.animation.activate_scene(character.animation.query_scene("full"))
            self.terminal.print()
            self.animate_chars()
            if final:
                self.active_chars = [character for character in self.active_chars if character.is_active]

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method."""
        for character in self.active_chars:
            character.tick()
