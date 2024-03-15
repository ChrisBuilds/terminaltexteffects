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
        
Example: terminaltexteffects spray --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --spray-position e --spray-volume 0.005 --movement-speed 0.4-1.0 --easing OUT_EXPO""",
    )
    effect_parser.set_defaults(effect_class=SprayEffect)
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
        "--spray-position",
        default="e",
        choices=["n", "ne", "e", "se", "s", "sw", "w", "nw", "center"],
        help="Position for the spray origin.",
    )
    effect_parser.add_argument(
        "--spray-volume",
        default=0.005,
        type=argtypes.positive_float,
        metavar="(float > 0)",
        help="Number of characters to spray per tick as a percent of the total number of characters.",
    )
    effect_parser.add_argument(
        "--movement-speed",
        type=argtypes.float_range,
        default=(0.4, 1.0),
        metavar="(float range e.g. 0.4-1.0)",
        help="Movement speed of the characters.",
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
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_data(self) -> None:
        """Prepares the data for the effect by starting all of the characters from a point based on SparklerPosition."""
        final_gradient = graphics.Gradient(self.args.final_gradient_stops, self.args.final_gradient_steps)

        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient.get_color_at_fraction(
                character.input_coord.row / self.terminal.output_area.top
            )
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

        for character in self.terminal.get_characters():
            character.motion.set_coordinate(spray_origin_map[self.spray_position])
            input_coord_path = character.motion.new_path(
                speed=random.uniform(self.args.movement_speed[0], self.args.movement_speed[1]), ease=self.args.easing
            )
            input_coord_path.new_waypoint(character.input_coord)
            character.event_handler.register_event(
                EventHandler.Event.PATH_ACTIVATED, input_coord_path, EventHandler.Action.SET_LAYER, 1
            )
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE, input_coord_path, EventHandler.Action.SET_LAYER, 0
            )
            droplet_scn = character.animation.new_scene()
            spray_gradient = graphics.Gradient(
                [random.choice(final_gradient.spectrum), self.character_final_color_map[character]], 7
            )
            droplet_scn.apply_gradient_to_symbols(spray_gradient, character.input_symbol, 20)
            character.animation.activate_scene(droplet_scn)
            character.motion.activate_path(input_coord_path)
            self.pending_chars.append(character)
        random.shuffle(self.pending_chars)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        volume = max(int(len(self.pending_chars) * self.args.spray_volume), 1)
        while self.pending_chars or self.active_chars:
            if self.pending_chars:
                for _ in range(random.randint(1, volume)):
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
