import argparse
import random

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
        "print",
        formatter_class=argtypes.CustomFormatter,
        help="Lines are printed one at a time following a print head. Print head performs line feed, carriage return.",
        description="Lines are printed one at a time following a print head. Print head performs line feed, carriage return.",
        epilog=f"""{argtypes.EASING_EPILOG}

Example: terminaltexteffects print --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 12 --print-head-return-speed 1.5 --print-speed 1 --print-head-easing IN_OUT_QUAD""",
    )
    effect_parser.set_defaults(effect_class=PrintEffect)
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


# TODO: apply gradients


class Row:
    def __init__(self, characters: list[EffectCharacter], character_color: str | int, typing_head_color: str | int):
        self.untyped_chars: list[EffectCharacter] = []
        self.typed_chars: list[EffectCharacter] = []
        blank_row_accounted = False
        for character in characters:
            if character.input_symbol == " ":
                if blank_row_accounted:
                    continue
                blank_row_accounted = True
            character.motion.set_coordinate(Coord(character.input_coord.column, 1))
            color_gradient = graphics.Gradient([typing_head_color, character_color], 5)
            typed_animation = character.animation.new_scene()
            typed_animation.apply_gradient_to_symbols(color_gradient, ("█", "▓", "▒", "░", character.input_symbol), 5)
            character.animation.activate_scene(typed_animation)
            self.untyped_chars.append(character)

    def move_up(self):
        for character in self.typed_chars:
            current_row = character.motion.current_coord.row
            character.motion.set_coordinate(Coord(character.motion.current_coord.column, current_row + 1))

    def type_char(self) -> EffectCharacter | None:
        if self.untyped_chars:
            next_char = self.untyped_chars.pop(0)
            self.typed_chars.append(next_char)
            return next_char
        return None


class PrintEffect:
    """Effect that moves a print head across the screen, printing characters, before performing a line feed and carriage return."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.pending_rows: list[Row] = []
        self.processed_rows: list[Row] = []
        self.typing_head = self.terminal.add_character("█", Coord(1, 1))
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_data(self) -> None:
        final_gradient = graphics.Gradient(self.args.final_gradient_stops, self.args.final_gradient_steps)

        for character in self.terminal.get_characters(
            fill_chars=True, sort=Terminal.CharacterSort.TOP_TO_BOTTOM_LEFT_TO_RIGHT
        ):
            self.character_final_color_map[character] = final_gradient.get_color_at_fraction(
                character.input_coord.row / self.terminal.output_area.top
            )

        input_rows = self.terminal.get_characters_grouped(
            grouping=self.terminal.CharacterGroup.ROW_TOP_TO_BOTTOM, fill_chars=True
        )
        for input_row in input_rows:
            self.pending_rows.append(
                Row(
                    input_row,
                    self.character_final_color_map[input_row[0]],
                    self.character_final_color_map[input_row[0]],
                )
            )

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        current_row: Row = self.pending_rows.pop(0)
        typing = True
        delay = 0
        last_column = 0
        final_gradient = graphics.Gradient(self.args.final_gradient_stops, self.args.final_gradient_steps)

        while self.active_chars or typing:
            if self.typing_head.motion.active_path:
                pass
            elif delay:
                delay -= 1
            else:
                delay = random.randint(0, 0)
                if current_row.untyped_chars:
                    for _ in range(min(len(current_row.untyped_chars), self.args.print_speed)):
                        next_char = current_row.type_char()
                        if next_char:
                            self.terminal.set_character_visibility(next_char, True)
                            self.active_chars.append(next_char)
                            last_column = next_char.input_coord.column
                else:
                    self.processed_rows.append(current_row)
                    if self.pending_rows:
                        for row in self.processed_rows:
                            row.move_up()
                        current_row = self.pending_rows.pop(0)
                        current_row_height = current_row.untyped_chars[0].input_coord.row
                        self.typing_head.motion.set_coordinate(Coord(last_column, 1))
                        self.terminal.set_character_visibility(self.typing_head, True)
                        self.typing_head.motion.paths.clear()
                        carriage_return_path = self.typing_head.motion.new_path(
                            speed=self.args.print_head_return_speed,
                            ease=self.args.print_head_easing,
                            id="carriage_return_path",
                        )
                        carriage_return_path.new_waypoint(Coord(1, 1))
                        self.typing_head.motion.activate_path(carriage_return_path)
                        self.typing_head.animation.set_appearance(
                            self.typing_head.input_symbol,
                            final_gradient.get_color_at_fraction(current_row_height / self.terminal.output_area.top),
                        )
                        self.typing_head.event_handler.register_event(
                            EventHandler.Event.PATH_COMPLETE,
                            carriage_return_path,
                            EventHandler.Action.CALLBACK,
                            EventHandler.Callback(self.terminal.set_character_visibility, False),
                        )
                        self.active_chars.append(self.typing_head)
                    else:
                        typing = False
            self.terminal.print()
            self.animate_chars()

            self.active_chars = [character for character in self.active_chars if character.is_active]
        self.terminal.print()

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method on all active characters."""
        for character in self.active_chars:
            character.tick()
