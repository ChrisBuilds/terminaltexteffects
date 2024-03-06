"""Effect that pours the characters into position from the top, bottom, left, or right."""

import argparse
from enum import Enum, auto

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
        "pour",
        formatter_class=argtypes.CustomFormatter,
        help="Pours the characters into position from the given direction.",
        description="pour | Pours the characters into position from the given direction.",
        epilog=f"""{argtypes.EASING_EPILOG}
        
Example: terminaltexteffects pour -a 0.004 --pour-direction down""",
    )
    effect_parser.set_defaults(effect_class=PourEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.nonnegative_float,
        default=0.004,
        help="Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have no impact beyond a certain lower threshold due to the processing speed of your device.",
    )
    effect_parser.add_argument(
        "--pour-direction",
        default="down",
        choices=["up", "down", "left", "right"],
        help="Direction the text will pour.",
    )
    effect_parser.add_argument(
        "--movement-speed",
        type=argtypes.positive_float,
        default=0.2,
        metavar="(float > 0)",
        help="Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )
    effect_parser.add_argument(
        "--gap",
        type=argtypes.nonnegative_int,
        default=1,
        metavar="(int >= 0)",
        help="Number of frames to wait between each character in the pour effect. Increase to slow down effect and create a more defined back and forth motion.",
    )
    effect_parser.add_argument(
        "--starting-color",
        type=argtypes.Color,
        default="ffffff",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color of the characters before the gradient starts.",
    )
    effect_parser.add_argument(
        "--pour-gradient-stops",
        type=argtypes.Color,
        nargs="+",
        default=["8A008A", "00D1FF", "FFFFFF"],
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the character gradient. If only one color is provided, the characters will be displayed in that color.",
    )
    effect_parser.add_argument(
        "--pour-gradient-steps",
        type=argtypes.positive_int,
        default=[12],
        metavar="(int > 0)",
        help="Number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )
    effect_parser.add_argument(
        "--pour-gradient-frames",
        type=argtypes.positive_int,
        default=25,
        metavar="(int > 0)",
        help="Number of frames to display each gradient step.",
    )
    effect_parser.add_argument(
        "--easing",
        default="IN_QUAD",
        type=argtypes.ease,
        help="Easing function to use for character movement.",
    )


class PourDirection(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()


class PourEffect:
    """Effect that pours the characters into position from the top, bottom, left, or right."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_groups: list[list[EffectCharacter]] = []
        self.active_characters: list[EffectCharacter] = []
        self.pour_direction = {
            "down": PourDirection.DOWN,
            "up": PourDirection.UP,
            "left": PourDirection.LEFT,
            "right": PourDirection.RIGHT,
        }.get(args.pour_direction, PourDirection.DOWN)
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_data(self) -> None:
        """Prepares the data for the effect by sorting the characters by the pour direction."""
        final_gradient = graphics.Gradient(self.args.pour_gradient_stops, self.args.pour_gradient_steps)

        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient.get_color_at_fraction(
                character.input_coord.row / self.terminal.output_area.top
            )

        sort_map = {
            PourDirection.DOWN: Terminal.CharacterGroup.ROW_BOTTOM_TO_TOP,
            PourDirection.UP: Terminal.CharacterGroup.ROW_TOP_TO_BOTTOM,
            PourDirection.LEFT: Terminal.CharacterGroup.COLUMN_LEFT_TO_RIGHT,
            PourDirection.RIGHT: Terminal.CharacterGroup.COLUMN_RIGHT_TO_LEFT,
        }
        groups = self.terminal.get_characters_grouped(grouping=sort_map[self.pour_direction])
        for i, group in enumerate(groups):
            for character in group:
                self.terminal.set_character_visibility(character, False)
                if self.pour_direction == PourDirection.DOWN:
                    character.motion.set_coordinate(Coord(character.input_coord.column, self.terminal.output_area.top))
                elif self.pour_direction == PourDirection.UP:
                    character.motion.set_coordinate(
                        Coord(character.input_coord.column, self.terminal.output_area.bottom)
                    )
                elif self.pour_direction == PourDirection.LEFT:
                    character.motion.set_coordinate(Coord(self.terminal.output_area.right, character.input_coord.row))
                elif self.pour_direction == PourDirection.RIGHT:
                    character.motion.set_coordinate(Coord(self.terminal.output_area.left, character.input_coord.row))
                input_coord_path = character.motion.new_path(
                    speed=self.args.movement_speed,
                    ease=self.args.easing,
                )
                input_coord_path.new_waypoint(character.input_coord)
                character.motion.activate_path(input_coord_path)

                pour_gradient = graphics.Gradient(
                    [self.args.starting_color, self.character_final_color_map[character]], self.args.pour_gradient_steps
                )
                pour_scn = character.animation.new_scene()
                pour_scn.apply_gradient_to_symbols(
                    pour_gradient, character.input_symbol, self.args.pour_gradient_frames
                )
                character.animation.activate_scene(pour_scn)
            if i % 2 == 0:
                self.pending_groups.append(group)
            else:
                self.pending_groups.append(group[::-1])

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        self.terminal.print()
        current_group = self.pending_groups.pop(0)
        gap = 0
        while self.pending_groups or self.active_characters or current_group:
            if not current_group:
                if self.pending_groups:
                    current_group = self.pending_groups.pop(0)
            if current_group:
                if not gap:
                    next_character = current_group.pop(0)
                    self.terminal.set_character_visibility(next_character, True)
                    self.active_characters.append(next_character)
                    gap = self.args.gap
                else:
                    gap -= 1
            self.animate_chars()
            self.active_characters = [character for character in self.active_characters if character.is_active]
            self.terminal.print()

    def animate_chars(self) -> None:
        """Animates the sliding characters."""
        for character in self.active_characters:
            character.tick()
