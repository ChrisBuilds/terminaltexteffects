"""Prints the input data one line at at time with a carriage return and line feed.

Classes:
    Print: Prints the input data one line at at time with a carriage return and line feed.
    PrintConfig: Configuration for the Print effect.
    PrintIterator: Effect iterator for the Print effect. Does not normally need to be called directly.
"""

from __future__ import annotations

import typing
from dataclasses import dataclass

from terminaltexteffects import Color, Coord, EffectCharacter, EventHandler, Gradient, easing
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argvalidators
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    """Get the effect class and its configuration class."""
    return Print, PrintConfig


@argclass(
    name="print",
    help="Lines are printed one at a time following a print head. Print head performs line feed, carriage return.",
    description="print | Lines are printed one at a time following a print head. Print head performs line feed, "
    "carriage return.",
    epilog=(
        f"{argvalidators.EASING_EPILOG} Example: terminaltexteffects print --final-gradient-stops 02b8bd "
        "c1f0e3 00ffa0 --final-gradient-steps 12 --print-head-return-speed 1.25 --print-speed 1 "
        "--print-head-easing IN_OUT_QUAD"
    ),
)
@dataclass
class PrintConfig(ArgsDataClass):
    """Configuration for the Print effect.

    Attributes:
        print_head_return_speed (float): Speed of the print head when performing a carriage return.
        print_speed (int): Speed of the print head when printing characters.
        print_head_easing (easing.EasingFunction): Easing function to use for print head movement.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one "
            "color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps "
            "will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.

    """

    print_head_return_speed: float = ArgField(
        cmd_name=["--print-head-return-speed"],
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=1.25,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Speed of the print head when performing a carriage return.",
    )  # type: ignore[assignment]
    "float : Speed of the print head when performing a carriage return."

    print_speed: int = ArgField(
        cmd_name=["--print-speed"],
        type_parser=argvalidators.PositiveInt.type_parser,
        default=1,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Speed of the print head when printing characters.",
    )  # type: ignore[assignment]
    "int : Speed of the print head when printing characters."

    print_head_easing: easing.EasingFunction = ArgField(
        cmd_name=["--print-head-easing"],
        default=easing.in_out_quad,
        type_parser=argvalidators.Ease.type_parser,
        help="Easing function to use for print head movement.",
    )  # type: ignore[assignment]
    "easing.EasingFunction : Easing function to use for print head movement."

    final_gradient_stops: tuple[Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("02b8bd"), Color("c1f0e3"), Color("00ffa0")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied across the canvas). "
        "If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    (
        "tuple[Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the "
        "characters will be displayed in that color."
    )

    final_gradient_steps: tuple[int, ...] | int = ArgField(
        cmd_name=["--final-gradient-steps"],
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a "
        "smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    (
        "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. More steps will "
        "create a smoother and longer gradient animation."
    )

    final_gradient_direction: Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=Gradient.Direction.DIAGONAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "Gradient.Direction : Direction of the final gradient."

    @classmethod
    def get_effect_class(cls) -> type[Print]:
        """Get the effect class associated with this configuration."""
        return Print


class PrintIterator(BaseEffectIterator[PrintConfig]):
    """Effect iterator for the Print effect."""

    class Row:
        """Row of characters to print."""

        def __init__(
            self,
            characters: list[EffectCharacter],
            character_final_color_map: dict[EffectCharacter, Color],
            typing_head_color: Color,
        ) -> None:
            """Initialize the row of characters to print.

            Args:
                characters (list[EffectCharacter]): List of characters to print.
                character_final_color_map (dict[EffectCharacter, Color]): Mapping of characters to their final colors.
                typing_head_color (Color): Color of the typing head.

            """
            self.untyped_chars: list[EffectCharacter] = []
            self.typed_chars: list[EffectCharacter] = []
            if all(character.input_symbol == " " for character in characters):
                characters = characters[:1]
            else:
                right_extent = max(
                    character.input_coord.column for character in characters if not character.is_fill_character
                )
                characters = [char for char in characters if char.input_coord.column <= right_extent]
            for character in characters:
                character.motion.set_coordinate(Coord(character.input_coord.column, 1))
                color_gradient = Gradient(typing_head_color, character_final_color_map[character], steps=5)
                typed_animation = character.animation.new_scene()
                typed_animation.apply_gradient_to_symbols(
                    ("█", "▓", "▒", "░", character.input_symbol),
                    5,
                    fg_gradient=color_gradient,
                )
                character.animation.activate_scene(typed_animation)
                self.untyped_chars.append(character)

        def move_up(self) -> None:
            """Move the row up one row."""
            for character in self.typed_chars:
                current_row = character.motion.current_coord.row
                character.motion.set_coordinate(Coord(character.motion.current_coord.column, current_row + 1))

        def type_char(self) -> EffectCharacter | None:
            """Type the next character in the row."""
            if self.untyped_chars:
                next_char = self.untyped_chars.pop(0)
                self.typed_chars.append(next_char)
                return next_char
            return None

    def __init__(self, effect: Print) -> None:
        """Initialize the iterator with the Print effect.

        Args:
            effect (Print): Print effect to apply to the input data.

        """
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.pending_rows: list[PrintIterator.Row] = []
        self.processed_rows: list[PrintIterator.Row] = []
        self.typing_head = self.terminal.add_character("█", Coord(1, 1))
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.build()

    def build(self) -> None:
        """Build the initial state of the effect."""
        self.final_gradient = Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = self.final_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.text_bottom,
            self.terminal.canvas.text_top,
            self.terminal.canvas.text_left,
            self.terminal.canvas.text_right,
            self.config.final_gradient_direction,
        )
        for character in self.terminal.get_characters(outer_fill_chars=True, inner_fill_chars=True):
            self.character_final_color_map[character] = final_gradient_mapping.get(
                character.input_coord,
                Color("ffffff"),
            )
        input_rows = self.terminal.get_characters_grouped(
            grouping=self.terminal.CharacterGroup.ROW_TOP_TO_BOTTOM,
            outer_fill_chars=True,
            inner_fill_chars=True,
        )
        for input_row in input_rows:
            self.pending_rows.append(
                PrintIterator.Row(
                    input_row,
                    self.character_final_color_map,
                    Color("ffffff"),
                ),
            )
        self._current_row: PrintIterator.Row = self.pending_rows.pop(0)
        self._typing = True
        self._last_column = 0

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        if self.active_characters or self._typing:
            if self.typing_head.motion.active_path:
                pass
            elif self._current_row.untyped_chars:
                for _ in range(min(len(self._current_row.untyped_chars), self.config.print_speed)):
                    next_char = self._current_row.type_char()
                    if next_char:
                        self.terminal.set_character_visibility(next_char, is_visible=True)
                        self.active_characters.add(next_char)
                        self._last_column = next_char.input_coord.column
            else:
                self.processed_rows.append(self._current_row)
                if self.pending_rows:
                    for row in self.processed_rows:
                        row.move_up()
                    self._current_row = self.pending_rows.pop(0)
                    if not all(
                        character.is_fill_character for character in self.processed_rows[-1].typed_chars
                    ) and not all(character.is_fill_character for character in self._current_row.untyped_chars):
                        left_extent = min(
                            [
                                character.input_coord.column
                                for character in self._current_row.untyped_chars
                                if not character.is_fill_character
                            ],
                        )
                        self._current_row.untyped_chars = [
                            char
                            for char in self._current_row.untyped_chars
                            if left_extent <= char.input_coord.column <= self.terminal.canvas.text_right
                        ]
                    self.typing_head.motion.set_coordinate(Coord(self._last_column, 1))
                    self.terminal.set_character_visibility(self.typing_head, is_visible=True)
                    self.typing_head.motion.paths.clear()
                    carriage_return_path = self.typing_head.motion.new_path(
                        speed=self.config.print_head_return_speed,
                        ease=self.config.print_head_easing,
                        path_id="carriage_return_path",
                    )
                    carriage_return_path.new_waypoint(
                        Coord(self._current_row.untyped_chars[0].input_coord.column, 1),
                    )
                    self.typing_head.motion.activate_path(carriage_return_path)

                    self.typing_head.event_handler.register_event(
                        EventHandler.Event.PATH_COMPLETE,
                        carriage_return_path,
                        EventHandler.Action.CALLBACK,
                        EventHandler.Callback(self.terminal.set_character_visibility, False),  # noqa: FBT003
                    )
                    self.active_characters.add(self.typing_head)
                else:
                    self._typing = False
            self.update()
            return self.frame
        raise StopIteration


class Print(BaseEffect[PrintConfig]):
    """Prints the input data one line at at time with a carriage return and line feed.

    Attributes:
        effect_config (PrintConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal

    """

    @property
    def _config_cls(self) -> type[PrintConfig]:
        return PrintConfig

    @property
    def _iterator_cls(self) -> type[PrintIterator]:
        return PrintIterator
