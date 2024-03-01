"""Creates a rain effect where characters fall from the top of the terminal."""

import argparse
import random

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.utils import graphics
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils.terminal import Terminal
from terminaltexteffects.utils.geometry import Coord


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "rain",
        formatter_class=argtypes.CustomFormatter,
        help="Rain characters from the top of the output area.",
        description="rain | Rain characters from the top of the output area.",
        epilog=f"""{argtypes.EASING_EPILOG}
        
Example: terminaltexteffects rain -a 0.01 --rain-colors 39 45 51 21""",
    )
    effect_parser.set_defaults(effect_class=RainEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.nonnegative_float,
        default=0.01,
        help="Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have no impact beyond a certain lower threshold due to the processing speed of your device.",
    )
    effect_parser.add_argument(
        "--rain-colors",
        type=argtypes.color,
        nargs="*",
        default=0,
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="List of colors for the rain drops. Colors are randomly chosen from the list.",
    )
    effect_parser.add_argument(
        "--final-color",
        type=argtypes.color,
        default="ffffff",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the final character.",
    )
    effect_parser.add_argument(
        "--movement-speed",
        type=argtypes.positive_float,
        default=0.15,
        metavar="(float > 0)",
        help="Falling speed of the rain drops.",
    )
    effect_parser.add_argument(
        "--easing",
        default="IN_QUART",
        type=argtypes.ease,
        help="Easing function to use for character movement.",
    )


class RainEffect:
    """Creates a rain effect where characters fall from the top of the output area."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.group_by_row: dict[int, list[EffectCharacter | None]] = {}

    def prepare_data(self) -> None:
        """Prepares the data for the effect by setting all characters y position to the input height and sorting by target y."""
        if self.args.rain_colors:
            rain_colors = self.args.rain_colors
        else:
            rain_colors = [39, 45, 51, 21, 117, 159]
        rain_characters = ["o", ".", ",", "*", "|"]

        for character in self.terminal._input_characters:
            raindrop_color = random.choice(rain_colors)
            rain_scn = character.animation.new_scene()
            rain_scn.add_frame(random.choice(rain_characters), 1, color=raindrop_color)
            raindrop_gradient = graphics.Gradient([raindrop_color, self.args.final_color], 7)
            fade_scn = character.animation.new_scene()
            for color in raindrop_gradient:
                fade_scn.add_frame(character.input_symbol, 5, color=color)
            character.animation.activate_scene(rain_scn)
            character.motion.set_coordinate(Coord(character.input_coord.column, self.terminal.output_area.top))
            input_path = character.motion.new_path(speed=self.args.movement_speed, ease=self.args.easing)
            input_path.new_waypoint(character.input_coord)

            character.event_handler.register_event(
                character.event_handler.Event.PATH_COMPLETE,
                input_path,
                character.event_handler.Action.ACTIVATE_SCENE,
                fade_scn,
            )
            character.motion.activate_path(input_path)
            self.pending_chars.append(character)
        for character in sorted(self.pending_chars, key=lambda c: c.input_coord.row):
            if character.input_coord.row not in self.group_by_row:
                self.group_by_row[character.input_coord.row] = []
            self.group_by_row[character.input_coord.row].append(character)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        self.pending_chars.clear()
        self.terminal.print()
        while self.group_by_row or self.active_chars or self.pending_chars:
            if not self.pending_chars and self.group_by_row:
                self.pending_chars.extend(self.group_by_row.pop(min(self.group_by_row.keys())))  # type: ignore
            if self.pending_chars:
                for _ in range(random.randint(1, 3)):
                    if self.pending_chars:
                        next_character = self.pending_chars.pop(random.randint(0, len(self.pending_chars) - 1))
                        self.terminal.set_character_visibility(next_character, True)
                        self.active_chars.append(next_character)

                    else:
                        break
            self.animate_chars()
            self.active_chars = [character for character in self.active_chars if character.is_active]
            self.terminal.print()

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method."""
        for character in self.active_chars:
            character.tick()
