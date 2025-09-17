"""Matrix digital rain effect.

Classes:
    Matrix: Matrix digital rain effect.
    MatrixConfig: Configuration for the Matrix effect.
    MatrixIterator: Iterator for the Matrix effect. Does not normally need to be called directly.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass

from terminaltexteffects import Animation, Color, ColorPair, Coord, EffectCharacter, Gradient, Terminal
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.argutils import ArgSpec, ParserSpec

MATRIX_SYMBOLS_COMMON = (
    "2",
    "5",
    "9",
    "8",
    "Z",
    "*",
    ")",
    ":",
    ".",
    '"',
    "=",
    "+",
    "-",
    "¦",
    "|",
    "_",
)
MATRIX_SYMBOLS_KATA = (
    "ｦ",
    "ｱ",
    "ｳ",
    "ｴ",
    "ｵ",
    "ｶ",
    "ｷ",
    "ｹ",
    "ｺ",
    "ｻ",
    "ｼ",
    "ｽ",
    "ｾ",
    "ｿ",
    "ﾀ",
    "ﾂ",
    "ﾃ",
    "ﾅ",
    "ﾆ",
    "ﾇ",
    "ﾈ",
    "ﾊ",
    "ﾋ",
    "ﾎ",
    "ﾏ",
    "ﾐ",
    "ﾑ",
    "ﾒ",
    "ﾓ",
    "ﾔ",
    "ﾕ",
    "ﾗ",
    "ﾘ",
    "ﾜ",
)


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "matrix", Matrix, MatrixConfig


@dataclass
class MatrixConfig(BaseConfig):
    """Configuration for the Matrix effect.

    Attributes:
        highlight_color (Color): Color for the bottom of the rain column.
        rain_color_gradient (tuple[Color, ...]): Tuple of colors for the rain gradient. If only one color is "
            "provided, the characters will be displayed in that color.
        rain_symbols (tuple[str, ...]): Tuple of symbols to use for the rain.
        rain_fall_delay_range (tuple[int, int]): Speed of the falling rain as determined by the delay between rows. "
            "Actual delay is randomly selected from the range.
        rain_column_delay_range (tuple[int, int]): Range of frames to wait between adding new rain columns.
        rain_time (int): Time, in seconds, to display the rain effect before transitioning to the input text.
        symbol_swap_chance (float): Chance of swapping a character's symbol on each tick.
        color_swap_chance (float): Chance of swapping a character's color on each tick.
        resolve_delay (int): Number of frames to wait between resolving the next group of characters. This is used "
            "to adjust the speed of the final resolve phase.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one color "
            "is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Int or Tuple of ints for the number of gradient steps to use. "
            "More steps will create a smoother and longer gradient animation.
        final_gradient_frames (int): Number of frames to display each gradient step. Increase to slow down the "
            "gradient animation.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.

    """

    parser_spec: ParserSpec = ParserSpec(
        name="matrix",
        help="Matrix digital rain effect.",
        description="matrix | Matrix digital rain effect.",
        epilog=(
            "Example: tte matrix --rain-color-gradient 92be92 185318 --rain-symbols 2 5 9 8 Z : . = + - ¦ _ "
            "--rain-fall-delay-range 8-25 --rain-column-delay-range 5-15 --rain-time 15 --symbol-swap-chance 0.005 "
            "--color-swap-chance 0.001 --resolve-delay 5 --final-gradient-stops 389c38 --final-gradient-steps 12 "
            "--final-gradient-frames 5 --final-gradient-direction vertical --highlight-color dbffdb"
        ),
    )
    highlight_color: Color = ArgSpec(
        name="--highlight-color",
        type=argutils.ColorArg.type_parser,
        default=Color("#dbffdb"),
        metavar=argutils.ColorArg.METAVAR,
        help="Color for the bottom of the rain column.",
    )  # pyright: ignore[reportAssignmentType]
    "Color : Color for the bottom of the rain column."

    rain_color_gradient: tuple[Color, ...] = ArgSpec(
        name="--rain-color-gradient",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        default=(Color("#92be92"), Color("#185318")),
        metavar=argutils.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the rain gradient. Colors are selected from the "
        "gradient randomly. If only one color is provided, the characters will be displayed in that color.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[Color, ...] : Tuple of colors for the rain gradient. If only one color is provided, the characters "
        "will be displayed in that color."
    )

    rain_symbols: tuple[str, ...] = ArgSpec(
        name="--rain-symbols",
        nargs="+",
        type=argutils.Symbol.type_parser,
        default=MATRIX_SYMBOLS_COMMON + MATRIX_SYMBOLS_KATA,
        metavar=argutils.Symbol.METAVAR,
        help="Space separated, unquoted, list of symbols to use for the rain.",
    )  # pyright: ignore[reportAssignmentType]
    "tuple[str, ...] : Tuple of symbols to use for the rain."

    rain_fall_delay_range: tuple[int, int] = ArgSpec(
        name="--rain-fall-delay-range",
        type=argutils.PositiveIntRange.type_parser,
        default=(2, 15),
        metavar=argutils.PositiveIntRange.METAVAR,
        help="Range for the speed of the falling rain as determined by the delay between rows. Actual delay is "
        "randomly selected from the range.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[int, int] : Speed of the falling rain as determined by the delay between rows. Actual delay is "
        "randomly selected from the range."
    )

    rain_column_delay_range: tuple[int, int] = ArgSpec(
        name="--rain-column-delay-range",
        type=argutils.PositiveIntRange.type_parser,
        default=(3, 9),
        metavar=argutils.PositiveIntRange.METAVAR,
        help="Range of frames to wait between adding new rain columns.",
    )  # pyright: ignore[reportAssignmentType]
    "tuple[int, int] : Range of frames to wait between adding new rain columns."

    rain_time: int = ArgSpec(
        name="--rain-time",
        type=argutils.PositiveInt.type_parser,
        default=15,
        metavar=argutils.PositiveInt.METAVAR,
        help="Time, in seconds, to display the rain effect before transitioning to the input text.",
    )  # pyright: ignore[reportAssignmentType]
    "int : Time, in seconds, to display the rain effect before transitioning to the input text."

    symbol_swap_chance: float = ArgSpec(
        name="--symbol-swap-chance",
        type=argutils.PositiveFloat.type_parser,
        default=0.005,
        metavar=argutils.PositiveFloat.METAVAR,
        help="Chance of swapping a character's symbol on each tick.",
    )  # pyright: ignore[reportAssignmentType]
    "float : Chance of swapping a character's symbol on each tick."

    color_swap_chance: float = ArgSpec(
        name="--color-swap-chance",
        type=argutils.PositiveFloat.type_parser,
        default=0.001,
        metavar=argutils.PositiveFloat.METAVAR,
        help="Chance of swapping a character's color on each tick.",
    )  # pyright: ignore[reportAssignmentType]
    "float : Chance of swapping a character's color on each tick."

    resolve_delay: int = ArgSpec(
        name="--resolve-delay",
        type=argutils.PositiveInt.type_parser,
        default=3,
        metavar=argutils.PositiveInt.METAVAR,
        help="Number of frames to wait between resolving the next group of characters. "
        "This is used to adjust the speed of the final resolve phase.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "int : Number of frames to wait between resolving the next group of characters. This is used to "
        "adjust the speed of the final resolve phase."
    )

    final_gradient_stops: tuple[Color, ...] = ArgSpec(
        name="--final-gradient-stops",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        default=(Color("#92be92"), Color("#336b33")),
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

    final_gradient_frames: int = ArgSpec(
        name="--final-gradient-frames",
        type=argutils.PositiveInt.type_parser,
        default=3,
        metavar=argutils.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step. Increase to slow down the gradient animation.",
    )  # pyright: ignore[reportAssignmentType]
    "int : Number of frames to display each gradient step. Increase to slow down the gradient animation."

    final_gradient_direction: Gradient.Direction = ArgSpec(
        name="--final-gradient-direction",
        type=argutils.GradientDirection.type_parser,
        default=Gradient.Direction.RADIAL,
        metavar=argutils.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # pyright: ignore[reportAssignmentType]
    "Gradient.Direction : Direction of the final gradient."


class MatrixIterator(BaseEffectIterator[MatrixConfig]):
    """Iterator for the Matrix effect."""

    class RainColumn:
        """Rain column for the Matrix effect."""

        def __init__(
            self,
            characters: list[EffectCharacter],
            terminal: Terminal,
            config: MatrixConfig,
            rain_colors: Gradient,
        ) -> None:
            """Initialize the rain column."""
            self.terminal = terminal
            self.config = config
            self.characters: list[EffectCharacter] = characters
            self.pending_characters: list[EffectCharacter] = []
            self.matrix_symbols: tuple[str, ...] = config.rain_symbols
            self.rain_colors = rain_colors
            self.column_drop_chance = 0.08
            self.setup_column("rain")

        def setup_column(self, phase: str) -> None:
            """Set up the rain column for the specified phase."""
            self.pending_characters.clear()
            self.phase = phase
            for character in self.characters:
                self.terminal.set_character_visibility(character, is_visible=False)
                self.pending_characters.append(character)
                character.motion.current_coord = character.input_coord
            self.visible_characters: list[EffectCharacter] = []
            if self.phase == "fill":
                self.base_rain_fall_delay = random.randint(
                    max(self.config.rain_fall_delay_range[0] // 3, 1),
                    max(self.config.rain_fall_delay_range[1] // 3, 1),
                )
            else:
                self.base_rain_fall_delay = random.randint(
                    self.config.rain_fall_delay_range[0],
                    self.config.rain_fall_delay_range[1],
                )
            self.active_rain_fall_delay = 0
            if self.phase == "rain":
                self.length = random.randint(max(1, int(len(self.characters) * 0.1)), len(self.characters))
            else:
                self.length = len(self.characters)
            self.hold_time = 0
            if self.length == len(self.characters):
                self.hold_time = random.randint(20, 45)

        def trim_column(self) -> None:
            """Trim the rain column."""
            if not self.visible_characters:
                return
            popped_char = self.visible_characters.pop(0)
            self.terminal.set_character_visibility(popped_char, is_visible=False)
            if len(self.visible_characters) > 1:
                self.fade_last_character()

        def drop_column(self) -> None:
            """Drop the rain column."""
            out_of_canvas = []
            for character in self.visible_characters:
                character.motion.current_coord = Coord(
                    character.motion.current_coord.column,
                    character.motion.current_coord.row - 1,
                )
                if character.motion.current_coord.row < self.terminal.canvas.bottom:
                    self.terminal.set_character_visibility(character, is_visible=False)
                    out_of_canvas.append(character)
            self.visible_characters = [char for char in self.visible_characters if char not in out_of_canvas]

        def fade_last_character(self) -> None:
            """Fade the last character in the rain column."""
            darker_color = Animation.adjust_color_brightness(random.choice(self.rain_colors[-3:]), 0.65)  # type: ignore[arg-type]
            self.visible_characters[0].animation.set_appearance(
                self.visible_characters[0].animation.current_character_visual.symbol,
                colors=ColorPair(fg=darker_color),
            )

        def resolve_char(self) -> EffectCharacter:
            """Resolve a character in the rain column.

            Returns:
                EffectCharacter: The resolved character.

            """
            return self.visible_characters.pop(random.randint(0, len(self.visible_characters) - 1))

        def tick(self) -> None:
            """Advance the rain column by one tick."""
            if not self.active_rain_fall_delay:
                if self.pending_characters:
                    next_char = self.pending_characters.pop(0)
                    next_char.animation.set_appearance(
                        random.choice(self.matrix_symbols),
                        colors=ColorPair(fg=self.config.highlight_color),
                    )
                    previous_character = self.visible_characters[-1] if self.visible_characters else None
                    # if there is a previous character, remove the highlight
                    if previous_character:
                        previous_character.animation.set_appearance(
                            previous_character.animation.current_character_visual.symbol,
                            colors=ColorPair(
                                fg=random.choice(self.rain_colors),
                            ),
                        )
                    self.terminal.set_character_visibility(next_char, is_visible=True)
                    self.visible_characters.append(next_char)

                # if no pending characters, but still visible characters, trim the column
                # unless the column is the full height of the canvas, then respect the hold
                # time before trimming
                elif self.visible_characters:
                    # adjust the bottom character color to remove the lightlight.
                    # always do this on the first hold frame, then
                    # randomly adjust the bottom character's color
                    # this is separately handled from the rest to prevent the
                    # highlight color from being replaced before appropriate
                    if (
                        self.visible_characters[-1].animation.current_character_visual.colors
                        and self.visible_characters[-1].animation.current_character_visual.colors.fg_color
                        == self.config.highlight_color
                    ):
                        self.visible_characters[-1].animation.set_appearance(
                            self.visible_characters[-1].animation.current_character_visual.symbol,
                            colors=ColorPair(fg=random.choice(self.rain_colors)),
                        )

                    if self.hold_time:
                        self.hold_time -= 1
                    elif self.phase == "rain":
                        if random.random() < self.column_drop_chance:
                            self.drop_column()
                        self.trim_column()

                # if the column is longer than the preset length while still adding characters, trim it
                if len(self.visible_characters) > self.length:
                    self.trim_column()
                self.active_rain_fall_delay = self.base_rain_fall_delay

            else:
                self.active_rain_fall_delay -= 1

            # randomly change the symbol and/or color of the characters
            next_color: Color | None
            for character in self.visible_characters:
                if random.random() < self.config.symbol_swap_chance:
                    next_symbol = random.choice(self.matrix_symbols)
                else:
                    next_symbol = character.animation.current_character_visual.symbol
                if random.random() < self.config.color_swap_chance:
                    next_color = random.choice(self.rain_colors)
                elif character.animation.current_character_visual.colors:
                    next_color = character.animation.current_character_visual.colors.fg_color
                else:
                    next_color = None
                character.animation.set_appearance(next_symbol, colors=ColorPair(fg=next_color))

    def __init__(self, effect: Matrix) -> None:
        """Initialize the Matrix effect iterator."""
        super().__init__(effect)
        self.pending_columns: list[MatrixIterator.RainColumn] = []
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.active_columns: list[MatrixIterator.RainColumn] = []
        self.full_columns: list[MatrixIterator.RainColumn] = []
        self.rain_colors = Gradient(*self.config.rain_color_gradient, steps=6)
        self.column_delay = 0
        self.resolve_delay = self.config.resolve_delay
        self.final_frame_shown = False
        self.rain_complete = False
        self.phase = "rain"
        self.build()
        self.rain_start = time.time()

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
        for character in self.terminal.get_characters():
            resolve_scn = character.animation.new_scene(scene_id="resolve")
            for color in Gradient(self.config.highlight_color, final_gradient_mapping[character.input_coord], steps=8):
                resolve_scn.add_frame(
                    character.input_symbol,
                    self.config.final_gradient_frames,
                    colors=ColorPair(fg=color),
                )

        for column_chars in self.terminal.get_characters_grouped(
            self.terminal.CharacterGroup.COLUMN_LEFT_TO_RIGHT,
            outer_fill_chars=True,
            inner_fill_chars=True,
        ):
            column_chars.reverse()
            self.pending_columns.append(
                MatrixIterator.RainColumn(column_chars, self.terminal, self.config, self.rain_colors),
            )
        random.shuffle(self.pending_columns)

    def __next__(self) -> str:  # noqa: PLR0915
        """Return the next frame in the animation."""
        if self.phase in ("rain", "fill"):
            if not self.column_delay:
                if self.phase == "rain":
                    for _ in range(random.randint(1, 3)):
                        if self.pending_columns:
                            self.active_columns.append(self.pending_columns.pop(0))
                else:
                    while self.pending_columns:
                        self.active_columns.append(self.pending_columns.pop(0))
                if self.phase == "rain":
                    self.column_delay = random.randint(
                        self.config.rain_column_delay_range[0],
                        self.config.rain_column_delay_range[1],
                    )
                else:
                    self.column_delay = 1
            else:
                self.column_delay -= 1
            for column in self.active_columns:
                column.tick()

                if not column.pending_characters:
                    if column.phase == "fill" and column not in self.full_columns:
                        self.full_columns.append(column)
                    elif not column.visible_characters:
                        column.setup_column(self.phase)
                        self.pending_columns.append(column)

            self.active_columns = [column for column in self.active_columns if column.visible_characters]
            if (
                self.phase == "fill"
                and not self.pending_columns
                and all((not column.pending_characters and column.phase == "fill") for column in self.active_columns)
            ):
                self.phase = "resolve"
                self.active_columns.clear()

            if (
                self.phase == "rain"
                and self.config.rain_time > 0
                and time.time() - self.rain_start > self.config.rain_time
            ):
                self.rain_complete = True
                self.phase = "fill"
                for column in self.active_columns:
                    column.hold_time = 0
                    column.column_drop_chance = 1
                for column in self.pending_columns:
                    column.setup_column(self.phase)

        elif self.phase == "resolve":
            for column in self.full_columns:
                column.tick()
                if column.visible_characters:
                    if not self.resolve_delay:
                        for _ in range(random.randint(1, 4)):
                            if column.visible_characters:
                                next_char = column.resolve_char()
                                if next_char.input_symbol != " ":
                                    next_char.animation.activate_scene("resolve")
                                    self.active_characters.add(next_char)
                                else:
                                    self.terminal.set_character_visibility(next_char, is_visible=False)
                        self.resolve_delay = self.config.resolve_delay
                    else:
                        self.resolve_delay -= 1

            self.full_columns = [column for column in self.full_columns if column.visible_characters]

        if (
            self.full_columns
            or self.active_columns
            or self.active_characters
            or self.pending_columns
            or not self.rain_complete
        ):
            self.update()
            return self.frame
        if not self.final_frame_shown:
            self.final_frame_shown = True
            self.update()
            return self.frame
        raise StopIteration


class Matrix(BaseEffect[MatrixConfig]):
    """Matrix digital rain effect.

    Attributes:
        effect_config (MatrixConfig): Configuration for the Matrix effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    @property
    def _config_cls(self) -> type[MatrixConfig]:
        return MatrixConfig

    @property
    def _iterator_cls(self) -> type[MatrixIterator]:
        return MatrixIterator
