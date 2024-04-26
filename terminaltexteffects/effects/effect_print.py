import random
import typing
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return Print, PrintConfig


@argclass(
    name="print",
    help="Lines are printed one at a time following a print head. Print head performs line feed, carriage return.",
    description="print | Lines are printed one at a time following a print head. Print head performs line feed, carriage return.",
    epilog=f"""{arg_validators.EASING_EPILOG}
    
Example: terminaltexteffects print --final-gradient-stops 02b8bd c1f0e3 00ffa0 --final-gradient-steps 12 --print-head-return-speed 1.25 --print-speed 1 --print-head-easing IN_OUT_QUAD""",
)
@dataclass
class PrintConfig(ArgsDataClass):
    """Configuration for the Print effect.

    Attributes:
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the gradient for the final color.
        print_head_return_speed (float): Speed of the print head when performing a carriage return.
        print_speed (int): Speed of the print head when printing characters.
        print_head_easing (typing.Callable): Easing function to use for print head movement."""

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("02b8bd", "c1f0e3", "00ffa0"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name=["--final-gradient-steps"],
        type_parser=arg_validators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] : Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=arg_validators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.DIAGONAL,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the gradient for the final color.",
    )  # type: ignore[assignment]
    "graphics.Gradient.Direction : Direction of the gradient for the final color."

    print_head_return_speed: float = ArgField(
        cmd_name=["--print-head-return-speed"],
        type_parser=arg_validators.PositiveFloat.type_parser,
        default=1.25,
        metavar=arg_validators.PositiveFloat.METAVAR,
        help="Speed of the print head when performing a carriage return.",
    )  # type: ignore[assignment]
    "float : Speed of the print head when performing a carriage return."

    print_speed: int = ArgField(
        cmd_name=["--print-speed"],
        type_parser=arg_validators.PositiveInt.type_parser,
        default=1,
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Speed of the print head when printing characters.",
    )  # type: ignore[assignment]
    "int : Speed of the print head when printing characters."

    print_head_easing: easing.EasingFunction = ArgField(
        cmd_name=["--print-head-easing"],
        default=easing.in_out_quad,
        type_parser=arg_validators.Ease.type_parser,
        help="Easing function to use for print head movement.",
    )  # type: ignore[assignment]
    "easing.EasingFunction : Easing function to use for print head movement."

    @classmethod
    def get_effect_class(cls):
        return Print


class _Row:
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


class PrintIterator(BaseEffectIterator[PrintConfig]):
    """Effect that moves a print head across the screen, printing characters, before performing a line feed and carriage return."""

    def __init__(self, effect: "Print"):
        super().__init__(effect)
        self._pending_chars: list[EffectCharacter] = []
        self._active_chars: list[EffectCharacter] = []
        self._pending_rows: list[_Row] = []
        self._processed_rows: list[_Row] = []
        self._typing_head = self._terminal.add_character("█", Coord(1, 1))
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}
        self._build()

    def _build(self) -> None:
        self.final_gradient = graphics.Gradient(
            *self._config.final_gradient_stops, steps=self._config.final_gradient_steps
        )
        final_gradient_mapping = self.final_gradient.build_coordinate_color_mapping(
            self._terminal.output_area.top, self._terminal.output_area.right, self._config.final_gradient_direction
        )
        for character in self._terminal.get_characters(fill_chars=True):
            self._character_final_color_map[character] = final_gradient_mapping[character.input_coord]
        input_rows = self._terminal.get_characters_grouped(
            grouping=self._terminal.CharacterGroup.ROW_TOP_TO_BOTTOM, fill_chars=True
        )
        for input_row in input_rows:
            self._pending_rows.append(
                _Row(
                    input_row,
                    self._character_final_color_map,
                    self._character_final_color_map[input_row[-1]],
                )
            )
        self._current_row: _Row = self._pending_rows.pop(0)
        self._typing = True
        self._delay = 0
        self._last_column = 0

    def __next__(self) -> str:
        if self._active_chars or self._typing:
            if self._typing_head.motion.active_path:
                pass
            elif self._delay:
                self._delay -= 1
            else:
                self._delay = random.randint(0, 0)
                if self._current_row.untyped_chars:
                    for _ in range(min(len(self._current_row.untyped_chars), self._config.print_speed)):
                        next_char = self._current_row.type_char()
                        if next_char:
                            self._terminal.set_character_visibility(next_char, True)
                            self._active_chars.append(next_char)
                            self._last_column = next_char.input_coord.column
                else:
                    self._processed_rows.append(self._current_row)
                    if self._pending_rows:
                        for row in self._processed_rows:
                            row.move_up()
                        self._current_row = self._pending_rows.pop(0)
                        current_row_height = self._current_row.untyped_chars[0].input_coord.row
                        self._typing_head.motion.set_coordinate(Coord(self._last_column, 1))
                        self._terminal.set_character_visibility(self._typing_head, True)
                        self._typing_head.motion.paths.clear()
                        carriage_return_path = self._typing_head.motion.new_path(
                            speed=self._config.print_head_return_speed,
                            ease=self._config.print_head_easing,
                            id="carriage_return_path",
                        )
                        carriage_return_path.new_waypoint(Coord(1, 1))
                        self._typing_head.motion.activate_path(carriage_return_path)
                        self._typing_head.animation.set_appearance(
                            self._typing_head.input_symbol,
                            self.final_gradient.get_color_at_fraction(
                                current_row_height / self._terminal.output_area.top
                            ),
                        )
                        self._typing_head.event_handler.register_event(
                            EventHandler.Event.PATH_COMPLETE,
                            carriage_return_path,
                            EventHandler.Action.CALLBACK,
                            EventHandler.Callback(self._terminal.set_character_visibility, False),
                        )
                        self._active_chars.append(self._typing_head)
                    else:
                        self._typing = False
            for character in self._active_chars:
                character.tick()
            next_frame = self._terminal.get_formatted_output_string()

            self._active_chars = [character for character in self._active_chars if character.is_active]
            return next_frame
        else:
            raise StopIteration


class Print(BaseEffect[PrintConfig]):
    """Prints the input data in a pouring fashion, one character at a time."""

    _config_cls = PrintConfig
    _iterator_cls = PrintIterator

    def __init__(self, input_data: str) -> None:
        super().__init__(input_data)
