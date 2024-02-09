import argparse, random

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils.terminal import Terminal
from terminaltexteffects.utils import graphics, motion, argtypes, easing


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "print",
        formatter_class=argtypes.CustomFormatter,
        help="Lines are printed one at a time following a print head. Print head performs line feed, carriage return.",
        description="Lines are printed one at a time following a print head. Print head performs line feed, carriage return.",
        epilog=f"""{argtypes.EASING_EPILOG}

Example: terminaltexteffects print -a 0.01 --print-head-color f3b462 --text-color f2ebc0 --print-head-return-speed 1.5 --print-speed 1 --print-head-easing IN_OUT_QUAD""",
    )
    effect_parser.set_defaults(effect_class=PrintEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.nonnegative_float,
        default=0.01,
        help="Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have no impact beyond a certain lower threshold due to the processing speed of your device.",
    )
    effect_parser.add_argument(
        "--print-head-color",
        type=argtypes.color,
        default="f3b462",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the print head as it moves across the terminal.",
    )
    effect_parser.add_argument(
        "--text-color",
        type=argtypes.color,
        default="f2ebc0",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the text.",
    )
    effect_parser.add_argument(
        "--print-head-return-speed",
        type=argtypes.positive_float,
        default=1.5,
        metavar="(float > 0)",
        help="Speed of the print head when performing a carriage return.",
    )
    effect_parser.add_argument(
        "--print-speed",
        type=argtypes.positive_int,
        default=1,
        metavar="(int >= 1)",
        help="Speed of the print head when printing characters.",
    )
    effect_parser.add_argument(
        "--print-head-easing",
        default="IN_OUT_QUAD",
        type=argtypes.ease,
        help="Easing function to use for print head movement.",
    )


class Row:
    def __init__(self, characters: list[EffectCharacter], character_color: str | int, typing_head_color: str | int):
        self.untyped_chars: list[EffectCharacter] = characters
        self.typed_chars: list[EffectCharacter] = []
        for character in self.untyped_chars:
            character.motion.set_coordinate(motion.Coord(character.input_coord.column, 1))
            color_gradient = graphics.Gradient([typing_head_color, character_color], 5)
            typed_animation = character.animation.new_scene("typed")
            for n, symbol in enumerate(("█", "▓", "▒", "░", character.input_symbol)):
                typed_animation.add_frame(symbol, 5, color=color_gradient.spectrum[n])
            character.animation.activate_scene(typed_animation)

    def move_up(self):
        for character in self.typed_chars:
            current_row = character.motion.current_coord.row
            character.motion.set_coordinate(motion.Coord(character.motion.current_coord.column, current_row + 1))

    def type_char(self) -> EffectCharacter | None:
        if self.untyped_chars:
            next_char = self.untyped_chars.pop(0)
            self.typed_chars.append(next_char)
            next_char.is_visible = True
            return next_char
        return None


class PrintHead(EffectCharacter):
    def __init__(
        self,
        symbol: str,
        input_column: int,
        input_row: int,
        color: str | int = "0000ff",
        speed: float = 1.5,
        ease=easing.in_quad,
    ):
        super().__init__(symbol, input_column, input_row)
        self.speed = speed
        self.ease = ease
        self.is_visible = False
        self.head_color_scn = self.animation.new_scene("head_color")
        self.head_color_scn.add_frame(symbol, 1, color=color)
        self.animation.activate_scene(self.head_color_scn)

    def carriage_return(self, starting_coord: motion.Coord):
        self.motion.set_coordinate(starting_coord)
        self.motion.paths.clear()
        carriage_return_path: motion.Path = self.motion.new_path("carriage_return", speed=self.speed, ease=self.ease)
        carriage_return_path.new_waypoint("home", motion.Coord(1, 1))
        self.event_handler.register_event(
            EventHandler.Event.PATH_COMPLETE,
            carriage_return_path,
            EventHandler.Action.SET_CHARACTER_VISIBILITY_STATE,
            False,
        )
        self.motion.activate_path(carriage_return_path)
        self.is_visible = True


class PrintEffect:
    """Effect that moves a print head across the screen, printing characters, before performing a line feed and carriage return."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.animating_chars: list[EffectCharacter] = []
        self.pending_rows: list[Row] = []
        self.processed_rows: list[Row] = []

    def prepare_data(self) -> None:
        """Prepares the data for the effect by ___."""
        input_rows = self.terminal.get_characters(sort_order=self.terminal.CharacterSort.ROW_TOP_TO_BOTTOM)
        for input_row in input_rows:
            self.pending_rows.append(Row(input_row, self.args.text_color, self.args.print_head_color))

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        current_row: Row = self.pending_rows.pop(0)
        typing = True
        delay = 0
        typing_head = PrintHead(
            "█",
            1,
            1,
            color=self.args.print_head_color,
            speed=self.args.print_head_return_speed,
            ease=self.args.print_head_easing,
        )
        self.terminal.characters.append(typing_head)
        last_column = 0
        while self.animating_chars or typing:
            if typing_head.motion.active_path:
                pass
            elif delay:
                delay -= 1
            else:
                delay = random.randint(0, 0)
                if current_row.untyped_chars:
                    for _ in range(min(len(current_row.untyped_chars), self.args.print_speed)):
                        next_char = current_row.type_char()
                        if next_char:
                            self.animating_chars.append(next_char)
                            last_column = next_char.input_coord.column
                else:
                    self.processed_rows.append(current_row)
                    if self.pending_rows:
                        for row in self.processed_rows:
                            row.move_up()
                        current_row = self.pending_rows.pop(0)
                        typing_head.carriage_return(motion.Coord(last_column, 1))
                        self.animating_chars.append(typing_head)
                    else:
                        typing = False
            self.terminal.print()
            self.animate_chars()

            # remove completed chars from animating chars
            self.animating_chars = [
                animating_char for animating_char in self.animating_chars if animating_char.is_active()
            ]
        self.terminal.print()

    def animate_chars(self) -> None:
        """Animates the characters by calling the move method and step animation. Move characters prior to stepping animation
        to ensure waypoint synced animations have the latest waypoint progress information."""
        for animating_char in self.animating_chars:
            animating_char.tick()
