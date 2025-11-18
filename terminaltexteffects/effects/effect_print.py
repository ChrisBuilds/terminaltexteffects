"""Prints the input data one line at at time with a carriage return and line feed.

Classes:
    Print: Prints the input data one line at at time with a carriage return and line feed.
    PrintConfig: Configuration for the Print effect.
    PrintIterator: Effect iterator for the Print effect. Does not normally need to be called directly.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass

from terminaltexteffects import Color, Coord, EffectCharacter, EventHandler, Gradient, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.argutils import ArgSpec, ParserSpec
from terminaltexteffects.utils.exceptions import DuplicateEventRegistrationError


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "print", Print, PrintConfig


@dataclass
class PrintConfig(BaseConfig):
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

    parser_spec: ParserSpec = ParserSpec(
        name="print",
        help="Lines are printed one at a time following a print head. Print head performs line feed, carriage return.",
        description="print | Lines are printed one at a time following a print head. Print head performs line feed, "
        "carriage return.",
        epilog=(
            f"{argutils.EASING_EPILOG} Example: terminaltexteffects print --final-gradient-stops 02b8bd "
            "c1f0e3 00ffa0 --final-gradient-steps 12 --print-head-return-speed 1.25 --print-speed 1 "
            "--print-head-easing IN_OUT_QUAD"
        ),
    )
    print_head_return_speed: float = ArgSpec(
        name="--print-head-return-speed",
        type=argutils.PositiveFloat.type_parser,
        default=1.5,
        metavar=argutils.PositiveFloat.METAVAR,
        help="Speed of the print head when performing a carriage return.",
    )  # pyright: ignore[reportAssignmentType]
    "float : Speed of the print head when performing a carriage return."

    print_speed: int = ArgSpec(
        name="--print-speed",
        type=argutils.PositiveInt.type_parser,
        default=2,
        metavar=argutils.PositiveInt.METAVAR,
        help="Speed of the print head when printing characters.",
    )  # pyright: ignore[reportAssignmentType]
    "int : Speed of the print head when printing characters."

    print_head_easing: easing.EasingFunction = ArgSpec(
        name="--print-head-easing",
        default=easing.in_out_quad,
        type=argutils.Ease.type_parser,
        help="Easing function to use for print head movement.",
    )  # pyright: ignore[reportAssignmentType]
    "easing.EasingFunction : Easing function to use for print head movement."

    final_gradient_stops: tuple[Color, ...] = ArgSpec(
        name="--final-gradient-stops",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=(Color("#02b8bd"), Color("#c1f0e3"), Color("#00ffa0")),
        metavar=argutils.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied across the canvas). "
        "If only one color is provided, the characters will be displayed in that color.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the "
        "characters will be displayed in that color."
    )

    final_gradient_steps: tuple[int, ...] | int = ArgSpec(
        name="--final-gradient-steps",
        type=argutils.PositiveInt.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=12,
        metavar=argutils.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a "
        "smoother and longer gradient animation.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. More steps will "
        "create a smoother and longer gradient animation."
    )

    final_gradient_direction: Gradient.Direction = ArgSpec(
        name="--final-gradient-direction",
        type=argutils.GradientDirection.type_parser,
        default=Gradient.Direction.DIAGONAL,
        metavar=argutils.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # pyright: ignore[reportAssignmentType]
    "Gradient.Direction : Direction of the final gradient."


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
                    3,
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
                Color("#ffffff"),
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
                    Color("#ffffff"),
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
                    with contextlib.suppress(DuplicateEventRegistrationError):
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
