"""Input text overflows and scrolls the terminal in a random order until eventually appearing ordered.

Classes:
    Overflow: Input text overflows and scrolls the terminal in a random order until eventually appearing ordered.
    OverflowConfig: Configuration for the Overflow effect.
    OverflowIterator: Iterates over the effect. Does not normally need to be called directly.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from terminaltexteffects import Color, ColorPair, Coord, EffectCharacter, Gradient, Terminal
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.argutils import ArgSpec, ParserSpec


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "overflow", Overflow, OverflowConfig


@dataclass
class OverflowConfig(BaseConfig):
    """Configuration for the Overflow effect.

    Attributes:
        overflow_gradient_stops (tuple[Color, ...]): Tuple of colors for the overflow gradient.
        overflow_cycles_range (tuple[int, int]): Lower and upper range of the number of cycles to overflow the text. "
            "Valid values are n >= 0.
        overflow_speed (int): Speed of the overflow effect. Valid values are n > 0.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one color "
            "is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps "
            "will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.

    """

    parser_spec: ParserSpec = ParserSpec(
        name="overflow",
        help="Input text overflows and scrolls the terminal in a random order until eventually appearing ordered.",
        description="overflow | Input text overflows and scrolls the terminal in a random order until eventually "
        "appearing ordered.",
        epilog=(
            "Example: terminaltexteffects overflow --final-gradient-stops 8A008A 00D1FF FFFFFF "
            "--final-gradient-steps 12 --overflow-gradient-stops f2ebc0 8dbfb3 f2ebc0 --overflow-cycles-range 2-4 "
            "--overflow-speed 3"
        ),
    )
    overflow_gradient_stops: tuple[Color, ...] = ArgSpec(
        name="--overflow-gradient-stops",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        default=(Color("f2ebc0"), Color("8dbfb3"), Color("f2ebc0")),
        metavar=argutils.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the overflow gradient.",
    )  # pyright: ignore[reportAssignmentType]
    "tuple[Color, ...] : Tuple of colors for the overflow gradient."

    overflow_cycles_range: tuple[int, int] = ArgSpec(
        name="--overflow-cycles-range",
        type=argutils.PositiveIntRange.type_parser,
        default=(2, 4),
        metavar=argutils.PositiveIntRange.METAVAR,
        help="Number of cycles to overflow the text.",
    )  # pyright: ignore[reportAssignmentType]
    "tuple[int, int] : Lower and upper range of the number of cycles to overflow the text."

    overflow_speed: int = ArgSpec(
        name="--overflow-speed",
        type=argutils.PositiveInt.type_parser,
        default=3,
        metavar=argutils.PositiveInt.METAVAR,
        help="Speed of the overflow effect.",
    )  # pyright: ignore[reportAssignmentType]
    "int : Speed of the overflow effect."

    final_gradient_stops: tuple[Color, ...] = ArgSpec(
        name="--final-gradient-stops",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        default=(Color("8A008A"), Color("00D1FF"), Color("FFFFFF")),
        metavar=argutils.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied across the canvas). If "
        "only one color is provided, the characters will be displayed in that color.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the "
        "characters will be displayed in that color."
    )

    final_gradient_steps: tuple[int, ...] | int = ArgSpec(
        name="--final-gradient-steps",
        type=argutils.PositiveInt.type_parser,
        nargs="+",
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
        default=Gradient.Direction.VERTICAL,
        metavar=argutils.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # pyright: ignore[reportAssignmentType]
    "Gradient.Direction : Direction of the final gradient."


class OverflowIterator(BaseEffectIterator[OverflowConfig]):
    """Iterates over the effect."""

    class Row:
        """Represents a row of characters in the overflow effect."""

        def __init__(self, characters: list[EffectCharacter], *, final: bool = False) -> None:
            """Initialize the row.

            Args:
                characters (list[EffectCharacter]): The characters in the row.
                final (bool, optional): This is the final state of the row. Defaults to False.

            """
            self.characters = characters
            self.current_index = 0
            self.final = final

        def move_up(self) -> None:
            """Move the row up by one row."""
            for character in self.characters:
                current_row = character.motion.current_coord.row
                character.motion.set_coordinate(Coord(character.motion.current_coord.column, current_row + 1))

        def setup(self) -> None:
            """Set up the row for display."""
            for character in self.characters:
                character.motion.set_coordinate(Coord(character.input_coord.column, 0))

        def set_color(self, fg_color: Color | None = None, bg_color: Color | None = None) -> None:
            """Set the color of the row."""
            for character in self.characters:
                character.animation.set_appearance(
                    character.input_symbol,
                    ColorPair(fg=fg_color, bg=bg_color),
                )

    def __init__(self, effect: Overflow) -> None:
        """Initialize the effect iterator."""
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.pending_rows: list[OverflowIterator.Row] = []
        self.active_rows: list[OverflowIterator.Row] = []
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.build()

    def build(self) -> None:
        """Build the initial state of the effect."""
        final_gradient = Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.text_bottom,
            self.terminal.canvas.text_top,
            self.terminal.canvas.text_left,
            self.terminal.canvas.text_right,
            self.config.final_gradient_direction,
        )
        for character in self.terminal.get_characters(outer_fill_chars=True, inner_fill_chars=True):
            self.character_final_color_map[character] = final_gradient_mapping.get(
                character.input_coord,
                Color("000000"),
            )
        lower_range, upper_range = self.config.overflow_cycles_range
        rows = self.terminal.get_characters_grouped(Terminal.CharacterGroup.ROW_TOP_TO_BOTTOM)
        if upper_range > 0:
            for _ in range(random.randint(lower_range, upper_range)):
                random.shuffle(rows)
                for row in rows:
                    copied_characters = []
                    # copy the character attributes to new characters
                    for character in row:
                        character_copy = self.terminal.add_character(character.input_symbol, character.input_coord)
                        character_copy.animation.existing_color_handling = self.terminal.config.existing_color_handling
                        character_copy._input_ansi_sequences = character._input_ansi_sequences
                        character_copy.animation.no_color = character.animation.no_color
                        character_copy.animation.use_xterm_colors = character.animation.use_xterm_colors
                        character_copy.animation.input_fg_color = character.animation.input_fg_color
                        character_copy.animation.input_bg_color = character.animation.input_bg_color
                        copied_characters.append(character_copy)
                    self.pending_rows.append(OverflowIterator.Row(copied_characters))
        # add rows in correct order to the end of self.pending_rows
        for row in self.terminal.get_characters_grouped(
            Terminal.CharacterGroup.ROW_TOP_TO_BOTTOM,
            outer_fill_chars=True,
            inner_fill_chars=True,
        ):
            next_row = OverflowIterator.Row(row)
            for character in next_row.characters:
                if self.terminal.config.existing_color_handling == "dynamic" and any(
                    (character.animation.input_fg_color, character.animation.input_bg_color),
                ):
                    character.animation.set_appearance(
                        character.animation.current_character_visual.symbol,
                        ColorPair(
                            fg=character.animation.input_fg_color,
                            bg=character.animation.input_bg_color,
                        ),
                    )
                else:
                    character.animation.set_appearance(
                        character.animation.current_character_visual.symbol,
                        ColorPair(fg=self.character_final_color_map[character]),
                    )
            self.pending_rows.append(OverflowIterator.Row(row, final=True))
        self._delay = 0
        self._overflow_gradient = Gradient(
            *self.config.overflow_gradient_stops,
            steps=max((self.terminal.canvas.top // max(1, len(self.config.overflow_gradient_stops) - 1)), 1),
        )

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        if self.pending_rows:
            if not self._delay:
                for _ in range(random.randint(1, self.config.overflow_speed)):
                    if self.pending_rows:
                        for row in self.active_rows:
                            row.move_up()
                            if not row.final:
                                row.set_color(
                                    self._overflow_gradient.spectrum[
                                        min(
                                            row.characters[0].motion.current_coord.row,
                                            len(self._overflow_gradient.spectrum) - 1,
                                        )
                                    ],
                                )
                        next_row = self.pending_rows.pop(0)
                        next_row.setup()
                        next_row.move_up()
                        if not next_row.final:
                            next_row.set_color(self._overflow_gradient.spectrum[0])
                        for character in next_row.characters:
                            self.terminal.set_character_visibility(character, is_visible=True)
                        self.active_rows.append(next_row)
                self._delay = random.randint(0, 3)

            else:
                self._delay -= 1
            self.active_rows = [
                row
                for row in self.active_rows
                if row.characters[0].motion.current_coord.row <= self.terminal.canvas.top
            ]
            self.update()
            return self.frame
        raise StopIteration


class Overflow(BaseEffect[OverflowConfig]):
    """Input text overflows and scrolls the terminal in a random order until eventually appearing ordered.

    Attributes:
        effect_config (OverflowConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    @property
    def _config_cls(self) -> type[OverflowConfig]:
        return OverflowConfig

    @property
    def _iterator_cls(self) -> type[OverflowIterator]:
        return OverflowIterator
