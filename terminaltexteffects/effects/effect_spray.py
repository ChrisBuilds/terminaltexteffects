"""Effect that draws the characters spawning at varying rates from a single point."""

import argparse
import random
from enum import Enum, auto

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects import base_character, base_effect
from terminaltexteffects.utils import graphics, motion
from terminaltexteffects.utils.terminal import Terminal


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "spray",
        help="Draws the characters spawning at varying rates from a single point.",
        description="spray | Draws the characters spawning at varying rates from a single point.",
        epilog=f"""{argtypes.EASING_EPILOG}
        
Example: terminaltexteffects spray -a 0.01 --spray-position center""",
    )
    effect_parser.set_defaults(effect_class=SprayEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.valid_animationrate,
        default=0.01,
        help="Time, in seconds, between animation steps.",
    )
    effect_parser.add_argument(
        "--spray-colors",
        type=argtypes.valid_color,
        nargs="*",
        default=0,
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="List of colors for the character spray. Colors are randomly chosen from the list.",
    )
    effect_parser.add_argument(
        "--final-color",
        type=argtypes.valid_color,
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
        type=argtypes.valid_speed,
        default=0.7,
        metavar="(float > 0)",
        help="Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )
    effect_parser.add_argument(
        "--easing",
        default="OUT_EXPO",
        type=argtypes.valid_ease,
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


class SprayEffect(base_effect.Effect):
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
        super().__init__(terminal, args)
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
            SprayPosition.CENTER: (
                self.terminal.output_area.right // 2,
                self.terminal.output_area.top // 2,
            ),
            SprayPosition.N: (self.terminal.output_area.right // 2, self.terminal.output_area.top),
            SprayPosition.NW: (self.terminal.output_area.left, self.terminal.output_area.top),
            SprayPosition.W: (self.terminal.output_area.left, self.terminal.output_area.top // 2),
            SprayPosition.SW: (self.terminal.output_area.left, self.terminal.output_area.bottom),
            SprayPosition.S: (self.terminal.output_area.right // 2, self.terminal.output_area.bottom),
            SprayPosition.SE: (self.terminal.output_area.right - 1, self.terminal.output_area.bottom),
            SprayPosition.E: (self.terminal.output_area.right - 1, self.terminal.output_area.top // 2),
            SprayPosition.NE: (self.terminal.output_area.right - 1, self.terminal.output_area.top),
        }

        for character in self.terminal.characters:
            character.motion.set_coordinate(*spray_origin_map[self.spray_position])
            character.motion.new_waypoint(
                "input_coord",
                character.input_coord.column,
                character.input_coord.row,
                speed=self.args.movement_speed,
                ease=self.args.easing,
            )
            if self.spray_colors:
                spray_color = random.choice(self.spray_colors)
                spray_gradient = graphics.gradient(spray_color, self.final_color, 7)
                for color in spray_gradient:
                    character.animator.add_effect_to_scene("droplet", character.input_symbol, color, 40)
                character.animator.activate_scene("droplet")
            character.motion.activate_waypoint("input_coord")
            self.pending_chars.append(character)
        random.shuffle(self.pending_chars)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        while self.pending_chars or self.animating_chars:
            if self.pending_chars:
                for _ in range(random.randint(1, self.args.spray_volume)):
                    if self.pending_chars:
                        next_character = self.pending_chars.pop()
                        next_character.is_active = True
                        self.animating_chars.append(next_character)

            self.animate_chars()
            self.terminal.print()
            self.animating_chars = [
                animating_char
                for animating_char in self.animating_chars
                if not animating_char.animator.is_active_scene_complete()
                or not animating_char.motion.movement_complete()
            ]

    def animate_chars(self) -> None:
        for animating_char in self.animating_chars:
            animating_char.animator.step_animation()
            animating_char.motion.move()
