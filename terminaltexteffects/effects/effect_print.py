import random
import typing
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils import easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return PrintEffect, PrintEffectArgs


@argclass(
    name="print",
    formatter_class=arg_validators.CustomFormatter,
    help="Lines are printed one at a time following a print head. Print head performs line feed, carriage return.",
    description="print | Lines are printed one at a time following a print head. Print head performs line feed, carriage return.",
    epilog=f"""{arg_validators.EASING_EPILOG}
    
Example: terminaltexteffects print --final-gradient-stops 02b8bd c1f0e3 00ffa0 --final-gradient-steps 12 --print-head-return-speed 1.25 --print-speed 1 --print-head-easing IN_OUT_QUAD""",
)
@dataclass
class PrintEffectArgs(ArgsDataClass):
    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("02b8bd", "c1f0e3", "00ffa0"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name=["--final-gradient-steps"],
        type_parser=arg_validators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=arg_validators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.DIAGONAL,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the gradient for the final color.",
    )  # type: ignore[assignment]
    print_head_return_speed: float = ArgField(
        cmd_name=["--print-head-return-speed"],
        type_parser=arg_validators.PositiveFloat.type_parser,
        default=1.25,
        metavar=arg_validators.PositiveFloat.METAVAR,
        help="Speed of the print head when performing a carriage return.",
    )  # type: ignore[assignment]
    print_speed: int = ArgField(
        cmd_name=["--print-speed"],
        type_parser=arg_validators.PositiveInt.type_parser,
        default=1,
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Speed of the print head when printing characters.",
    )  # type: ignore[assignment]
    print_head_easing: typing.Callable = ArgField(
        cmd_name=["--print-head-easing"],
        default=easing.in_out_quad,
        type_parser=arg_validators.Ease.type_parser,
        help="Easing function to use for print head movement.",
    )  # type: ignore[assignment]

    @classmethod
    def get_effect_class(cls):
        return PrintEffect


class Row:
    def __init__(
        self,
        characters: list[EffectCharacter],
        character_final_color_map: dict[EffectCharacter, graphics.Color],
        typing_head_color: str | int,
    ):
        self.untyped_chars: list[EffectCharacter] = []
        self.typed_chars: list[EffectCharacter] = []
        blank_row_accounted = False
        for character in characters:
            if character.input_symbol == " ":
                if blank_row_accounted:
                    continue
                blank_row_accounted = True
            character.motion.set_coordinate(Coord(character.input_coord.column, 1))
            color_gradient = graphics.Gradient(typing_head_color, character_final_color_map[character], steps=5)
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

    def __init__(self, terminal: Terminal, args: PrintEffectArgs):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.pending_rows: list[Row] = []
        self.processed_rows: list[Row] = []
        self.typing_head = self.terminal.add_character("█", Coord(1, 1))
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_data(self) -> None:
        final_gradient = graphics.Gradient(*self.args.final_gradient_stops, steps=self.args.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.args.final_gradient_direction
        )
        for character in self.terminal.get_characters(fill_chars=True):
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
        input_rows = self.terminal.get_characters_grouped(
            grouping=self.terminal.CharacterGroup.ROW_TOP_TO_BOTTOM, fill_chars=True
        )
        for input_row in input_rows:
            self.pending_rows.append(
                Row(
                    input_row,
                    self.character_final_color_map,
                    self.character_final_color_map[input_row[-1]],
                )
            )

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        current_row: Row = self.pending_rows.pop(0)
        typing = True
        delay = 0
        last_column = 0
        final_gradient = graphics.Gradient(*self.args.final_gradient_stops, steps=self.args.final_gradient_steps)

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
