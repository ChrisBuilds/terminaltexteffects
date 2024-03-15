import argparse
import random

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils import graphics
from terminaltexteffects.utils.terminal import Terminal


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "burn",
        help="Burns vertically in the output area.",
        description="burn | Burn the output area.",
        epilog="Example: terminaltexteffects burn --burned-color 252525 --flame-color ff9600 --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12",
    )
    effect_parser.set_defaults(effect_class=BurnEffect)
    effect_parser.add_argument(
        "--burned-color",
        type=argtypes.color,
        default="252525",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color faded toward as blocks burn. Defaults to 252525",
    )
    effect_parser.add_argument(
        "--flame-color",
        type=argtypes.color,
        default="ff9600",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the flame. Defaults to 0",
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


class BurnEffect:
    """Effect that burns up the screen."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

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
        final_gradient = graphics.Gradient(self.args.final_gradient_stops, self.args.final_gradient_steps)
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient.get_color_at_fraction(
                character.input_coord.row / self.terminal.output_area.top
            )

        fire_gradient = graphics.Gradient(["ffffff", self.args.flame_color], 12)
        burned_gradient = graphics.Gradient([self.args.flame_color, self.args.burned_color], 7)
        groups = {
            column_index: column
            for column_index, column in enumerate(
                self.terminal.get_characters_grouped(grouping=self.terminal.CharacterGroup.COLUMN_LEFT_TO_RIGHT)
            )
        }

        def groups_remaining(rows) -> bool:
            return any(row for row in rows.values())

        while groups_remaining(groups):
            keys = [key for key in groups.keys() if groups[key]]
            next_char = groups[random.choice(keys)].pop(0)
            self.terminal.set_character_visibility(next_char, False)
            construct_scn = next_char.animation.new_scene()
            g_start = 0
            for _, block in enumerate(vertical_build_order[:5]):
                for color in fire_gradient.spectrum[g_start : g_start + 3]:
                    construct_scn.add_frame(block, 30, color=color)
                g_start += 2

            g_start = 0
            for _, block in enumerate(vertical_build_order[4:]):
                for color in burned_gradient.spectrum[g_start : g_start + 3]:
                    construct_scn.add_frame(block, 30, color=color)
                g_start += 2

            construct_scn.add_frame(next_char.input_symbol, 1, color=self.character_final_color_map[next_char])
            next_char.animation.activate_scene(construct_scn)
            self.pending_chars.append(next_char)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        while self.pending_chars or self.active_chars:
            if self.pending_chars:
                next_char = self.pending_chars.pop(0)
                self.terminal.set_character_visibility(next_char, True)
                self.active_chars.append(next_char)

            self.animate_chars()

            self.active_chars = [character for character in self.active_chars if character.is_active]
            self.terminal.print()

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method."""
        for character in self.active_chars:
            character.animation.step_animation()
