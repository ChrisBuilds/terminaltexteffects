import argparse
import random

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
        "bouncyballs",
        formatter_class=argtypes.CustomFormatter,
        help="Characters are bouncy balls falling from the top of the output area.",
        description="bouncyball | Characters are bouncy balls falling from the top of the output area.",
        epilog=f"""{argtypes.EASING_EPILOG}
        
Example: terminaltexteffects bouncyballs --ball-colors 00ff00 ff0000 0000ff --ball-symbols "o" "*" "O" "0" "." --final-gradient-stops 00ff00 ff0000 0000ff --final-gradient-steps 12 --ball-delay 7 --movement-speed 0.25 --easing OUT_BOUNCE""",
    )
    effect_parser.set_defaults(effect_class=BouncyBallsEffect)
    effect_parser.add_argument(
        "--ball-colors",
        type=argtypes.color,
        nargs="+",
        default=["8A008A", "00D1FF", "FFFFFF"],
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated list of colors from which ball colors will be randomly selected. If no colors are provided, the colors are random.",
    )
    effect_parser.add_argument(
        "--ball-symbols",
        type=argtypes.symbol,
        nargs="+",
        default=["*", "o", "O", "0", "."],
        metavar="(ASCII/UTF-8 character string)",
        help="Space separated list of symbols to use for the balls.",
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
        "--ball-delay",
        type=argtypes.nonnegative_int,
        default=7,
        metavar="(int >= 0)",
        help="Number of animation steps between ball drops, increase to reduce ball drop rate.",
    )
    effect_parser.add_argument(
        "--movement-speed",
        type=argtypes.positive_float,
        default=0.25,
        metavar="(float > 0)",
        help="Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )
    effect_parser.add_argument(
        "--easing",
        default="OUT_BOUNCE",
        type=argtypes.ease,
        help="Easing function to use for character movement.",
    )


class BouncyBallsEffect:
    """Effect that displays the text as bouncy balls falling from the top of the output area."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.group_by_row: dict[int, list[EffectCharacter | None]] = {}
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_data(self) -> None:
        """Prepares the data for the effect by assigning colors and waypoints and
        organizing the characters by row."""
        final_gradient = graphics.Gradient(self.args.final_gradient_stops, self.args.final_gradient_steps)

        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient.get_color_at_fraction(
                character.input_coord.row / self.terminal.output_area.top
            )
            color = random.choice(self.args.ball_colors)
            symbol = random.choice(self.args.ball_symbols)
            ball_scene = character.animation.new_scene()
            ball_scene.add_frame(symbol, 1, color=color)
            final_scene = character.animation.new_scene()
            char_final_gradient = graphics.Gradient([color, self.character_final_color_map[character]], 10)
            final_scene.apply_gradient_to_symbols(char_final_gradient, character.input_symbol, 10)
            character.motion.set_coordinate(
                Coord(character.input_coord.column, int(self.terminal.output_area.top * random.uniform(1.0, 1.5)))
            )
            input_coord_path = character.motion.new_path(speed=self.args.movement_speed, ease=self.args.easing)
            input_coord_path.new_waypoint(character.input_coord)
            character.motion.activate_path(input_coord_path)
            character.animation.activate_scene(ball_scene)
            character.event_handler.register_event(
                character.event_handler.Event.PATH_COMPLETE,
                input_coord_path,
                character.event_handler.Action.ACTIVATE_SCENE,
                final_scene,
            )
            self.pending_chars.append(character)
        for character in sorted(self.pending_chars, key=lambda c: c.input_coord.row):
            if character.input_coord.row not in self.group_by_row:
                self.group_by_row[character.input_coord.row] = []
            self.group_by_row[character.input_coord.row].append(character)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        self.pending_chars.clear()
        ball_delay = 0
        while self.group_by_row or self.active_chars or self.pending_chars:
            if not self.pending_chars and self.group_by_row:
                self.pending_chars.extend(self.group_by_row.pop(min(self.group_by_row.keys())))  # type: ignore
            if self.pending_chars:
                if ball_delay == 0:
                    for _ in range(random.randint(2, 6)):
                        if self.pending_chars:
                            next_character = self.pending_chars.pop(random.randint(0, len(self.pending_chars) - 1))
                            self.terminal.set_character_visibility(next_character, True)
                            self.active_chars.append(next_character)
                        else:
                            break
                    ball_delay = self.args.ball_delay
                else:
                    ball_delay -= 1

            self.animate_chars()
            self.active_chars = [character for character in self.active_chars if character.is_active]
            self.terminal.print()

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method."""
        for character in self.active_chars:
            character.tick()
