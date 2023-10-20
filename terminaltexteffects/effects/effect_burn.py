import argparse
import random

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils.terminal import Terminal
from terminaltexteffects.utils import graphics, argtypes


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "burn",
        help="Burns vertically in the output area.",
        description="burn | Burn the output area.",
        epilog="Example: terminaltexteffects burn -a 0.003 --flame-color ff9600 --burned-color 252525",
    )
    effect_parser.set_defaults(effect_class=BurnEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.valid_animationrate,
        default=0.003,
        help="Time between animation steps. Defaults to 0.03 seconds.",
    )
    effect_parser.add_argument(
        "--burned-color",
        type=argtypes.valid_color,
        default="252525",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color faded toward as blocks burn. Defaults to 252525",
    )
    effect_parser.add_argument(
        "--flame-color",
        type=argtypes.valid_color,
        default="ff9600",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the flame. Defaults to 0",
    )
    effect_parser.add_argument(
        "--final-color",
        type=argtypes.valid_color,
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the final character. Will leave as system default if not provided.",
    )


class BurnEffect:
    """Effect that burns up the screen."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.animating_chars: list[EffectCharacter] = []

    def prepare_data(self) -> None:
        """Prepares the data for the effect by building the burn animation and organizing the data into columns."""
        vertical_build_order = [
            ".",
            "▖",
            "▄",
            "▙",
            "█",
            "▜",
            "▀",
        ]
        fire_gradient = graphics.Gradient("ffffff", self.args.flame_color, 12)
        burned_gradient = graphics.Gradient(self.args.flame_color, self.args.burned_color, 7)
        groups = self.terminal.input_by_column()
        for column in groups.values():
            column.reverse()

        def groups_remaining(rows) -> bool:
            return any(row for row in rows.values())

        while groups_remaining(groups):
            keys = [key for key in groups.keys() if groups[key]]
            next_char = groups[random.choice(keys)].pop(0)
            next_char.is_active = False
            construct_scn = next_char.animation.new_scene("construct")
            g_start = 0
            for _, block in enumerate(vertical_build_order[:5]):
                for color in fire_gradient.colors[g_start : g_start + 3]:
                    construct_scn.add_frame(block, 30, color=color)
                g_start += 2

            g_start = 0
            for _, block in enumerate(vertical_build_order[4:]):
                for color in burned_gradient.colors[g_start : g_start + 3]:
                    construct_scn.add_frame(block, 30, color=color)
                g_start += 2

            construct_scn.add_frame(next_char.input_symbol, 1, color=self.args.final_color)
            next_char.animation.activate_scene(construct_scn)
            self.pending_chars.append(next_char)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        while self.pending_chars or self.animating_chars:
            if self.pending_chars:
                next_char = self.pending_chars.pop(0)
                next_char.is_active = True
                self.animating_chars.append(next_char)

            self.animate_chars()

            self.animating_chars = [
                animating_char
                for animating_char in self.animating_chars
                if not animating_char.animation.active_scene_is_complete()
            ]
            self.terminal.print()

    def animate_chars(self) -> None:
        """Animates the characters by calling the move method and step animation."""
        for animating_char in self.animating_chars:
            animating_char.animation.step_animation()
