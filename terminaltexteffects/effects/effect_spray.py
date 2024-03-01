"""Effect that draws the characters spawning at varying rates from a single point."""

import argparse
import random
from enum import Enum, auto

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils import graphics
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "spray",
        formatter_class=argtypes.CustomFormatter,
        help="Draws the characters spawning at varying rates from a single point.",
        description="spray | Draws the characters spawning at varying rates from a single point.",
        epilog=f"""{argtypes.EASING_EPILOG}
        
Example: terminaltexteffects spray -a 0.01 --spray-position center --spray-volume 5 --movement-speed 0.7 --easing OUT_EXPO --spray-colors 10 11 12 --final-color 0""",
    )
    effect_parser.set_defaults(effect_class=SprayEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.nonnegative_float,
        default=0.01,
        help="Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have no impact beyond a certain lower threshold due to the processing speed of your device.",
    )
    effect_parser.add_argument(
        "--spray-colors",
        type=argtypes.color,
        nargs="*",
        default=0,
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="List of colors for the character spray. Colors are randomly chosen from the list.",
    )
    effect_parser.add_argument(
        "--final-color",
        type=argtypes.color,
        default="ffffff",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the final character.",
    )
    effect_parser.add_argument(
        "--spray-position",
        default="e",
        choices=["n", "ne", "e", "se", "s", "sw", "w", "nw", "center"],
        help="Position for the spray origin.",
    )
    effect_parser.add_argument(
        "--spray-volume",
        default=5,
        type=argtypes.positive_int,
        metavar="(int > 0)",
        help="Maximum number of characters to spray at a time.",
    )
    effect_parser.add_argument(
        "--movement-speed",
        type=argtypes.positive_float,
        default=0.7,
        metavar="(float > 0)",
        help="Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )
    effect_parser.add_argument(
        "--easing",
        default="OUT_EXPO",
        type=argtypes.ease,
        help="Easing function to use for character movement.",
    )


class SprayPosition(Enum):
    """Position for the spray origin."""

    N = auto()
    NE = auto()
    E = auto()
    SE = auto()
    S = auto()
    SW = auto()
    W = auto()
    NW = auto()
    CENTER = auto()


class SprayEffect:
    """Effect that draws the characters spawning at varying rates from a single point."""

    def __init__(
        self,
        terminal: Terminal,
        args: argparse.Namespace,
    ):
        """Effect that draws the characters spawning at varying rates from a single point.

        Args:
            terminal (Terminal): terminal to use for the effect
            args (argparse.Namespace): arguments from argparse
        """
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.spray_position = {
            "n": SprayPosition.N,
            "ne": SprayPosition.NE,
            "e": SprayPosition.E,
            "se": SprayPosition.SE,
            "s": SprayPosition.S,
            "sw": SprayPosition.SW,
            "w": SprayPosition.W,
            "nw": SprayPosition.NW,
            "center": SprayPosition.CENTER,
        }.get(args.spray_position, SprayPosition.E)
        self.spray_colors = args.spray_colors
        self.final_color = args.final_color

    def prepare_data(self) -> None:
        """Prepares the data for the effect by starting all of the characters from a point based on SparklerPosition."""
        spray_origin_map = {
            SprayPosition.CENTER: (self.terminal.output_area.center),
            SprayPosition.N: Coord(self.terminal.output_area.right // 2, self.terminal.output_area.top),
            SprayPosition.NW: Coord(self.terminal.output_area.left, self.terminal.output_area.top),
            SprayPosition.W: Coord(self.terminal.output_area.left, self.terminal.output_area.top // 2),
            SprayPosition.SW: Coord(self.terminal.output_area.left, self.terminal.output_area.bottom),
            SprayPosition.S: Coord(self.terminal.output_area.right // 2, self.terminal.output_area.bottom),
            SprayPosition.SE: Coord(self.terminal.output_area.right - 1, self.terminal.output_area.bottom),
            SprayPosition.E: Coord(self.terminal.output_area.right - 1, self.terminal.output_area.top // 2),
            SprayPosition.NE: Coord(self.terminal.output_area.right - 1, self.terminal.output_area.top),
        }

        for character in self.terminal._input_characters:
            character.motion.set_coordinate(spray_origin_map[self.spray_position])
            input_coord_path = character.motion.new_path(speed=self.args.movement_speed, ease=self.args.easing)
            input_coord_path.new_waypoint(character.input_coord)
            character.event_handler.register_event(
                EventHandler.Event.PATH_ACTIVATED, input_coord_path, EventHandler.Action.SET_LAYER, 1
            )
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE, input_coord_path, EventHandler.Action.SET_LAYER, 0
            )
            if self.spray_colors:
                droplet_scn = character.animation.new_scene()
                spray_color = random.choice(self.spray_colors)
                spray_gradient = graphics.Gradient([spray_color, self.final_color], 7)
                for color in spray_gradient:
                    droplet_scn.add_frame(character.input_symbol, 40, color=color)
                character.animation.activate_scene(droplet_scn)
            character.motion.activate_path(input_coord_path)
            self.pending_chars.append(character)
        random.shuffle(self.pending_chars)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        while self.pending_chars or self.active_chars:
            if self.pending_chars:
                for _ in range(random.randint(1, self.args.spray_volume)):
                    if self.pending_chars:
                        next_character = self.pending_chars.pop()
                        self.terminal.set_character_visibility(next_character, True)
                        self.active_chars.append(next_character)

            self.animate_chars()
            self.terminal.print()
            self.active_chars = [character for character in self.active_chars if character.is_active]

    def animate_chars(self) -> None:
        for character in self.active_chars:
            character.tick()
