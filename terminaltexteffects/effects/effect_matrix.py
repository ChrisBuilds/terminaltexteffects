"""Matrix digital rain effect.

Classes:
    Matrix: Matrix digital rain effect.
    MatrixConfig: Configuration for the Matrix effect.
    MatrixIterator: Iterator for the Matrix effect. Does not normally need to be called directly.
"""

from __future__ import annotations

import random
import time
import typing
from dataclasses import dataclass

import terminaltexteffects.utils.argvalidators as argvalidators
from terminaltexteffects.engine.animation import Animation
from terminaltexteffects.engine.base_character import EffectCharacter
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.motion import Coord
from terminaltexteffects.engine.terminal import Terminal
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.graphics import Color, Gradient

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


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return Matrix, MatrixConfig


@argclass(
    name="matrix",
    help="Matrix digital rain effect.",
    description="matrix | Matrix digital rain effect.",
    epilog="""Example: tte matrix --rain-color-gradient 92be92 185318 --rain-symbols 2 5 9 8 Z : . = + - ¦ _ --rain-fall-delay-range 8-25 --rain-column-delay-range 5-15 --rain-time 15 --symbol-swap-chance 0.005 --color-swap-chance 0.001 --resolve-delay 5 --final-gradient-stops 389c38 --final-gradient-steps 12 --final-gradient-frames 5 --final-gradient-direction vertical --highlight-color dbffdb""",
)
@dataclass
class MatrixConfig(ArgsDataClass):
    """Configuration for the Matrix effect.

    Attributes:
        highlight_color (Color): Color for the bottom of the rain column.
        rain_color_gradient (tuple[Color, ...]): Tuple of colors for the rain gradient. If only one color is provided, the characters will be displayed in that color.
        rain_symbols (tuple[str, ...]): Tuple of symbols to use for the rain.
        rain_fall_delay_range (tuple[int, int]): Speed of the falling rain as determined by the delay between rows. Actual delay is randomly selected from the range.
        rain_column_delay_range (tuple[int, int]): Range of frames to wait between adding new rain columns.
        rain_time (int): Time, in seconds, to display the rain effect before transitioning to the input text.
        symbol_swap_chance (float): Chance of swapping a character's symbol on each tick.
        color_swap_chance (float): Chance of swapping a character's color on each tick.
        resolve_delay (int): Number of frames to wait between resolving the next group of characters. This is used to adjust the speed of the final resolve phase.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Int or Tuple of ints for the number of gradient steps to use. More steps will create a smoother and longer gradient animation.
        final_gradient_frames (int): Number of frames to display each gradient step. Increase to slow down the gradient animation.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.
    """

    highlight_color: Color = ArgField(
        cmd_name=["--highlight-color"],
        type_parser=argvalidators.ColorArg.type_parser,
        default=Color("dbffdb"),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Color for the bottom of the rain column.",
    )  # type: ignore[assignment]
    "Color : Color for the bottom of the rain column."

    rain_color_gradient: tuple[Color, ...] = ArgField(
        cmd_name=["--rain-color-gradient"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("92be92"), Color("185318")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the rain gradient. Colors are selected from the gradient randomly. If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[Color, ...] : Tuple of colors for the rain gradient. If only one color is provided, the characters will be displayed in that color."

    rain_symbols: tuple[str, ...] = ArgField(
        cmd_name=["--rain-symbols"],
        nargs="+",
        type_parser=argvalidators.Symbol.type_parser,
        default=MATRIX_SYMBOLS_COMMON + MATRIX_SYMBOLS_KATA,
        metavar=argvalidators.Symbol.METAVAR,
        help="Space separated, unquoted, list of symbols to use for the rain.",
    )  # type: ignore[assignment]
    "tuple[str, ...] : Tuple of symbols to use for the rain."

    rain_fall_delay_range: tuple[int, int] = ArgField(
        cmd_name=["--rain-fall-delay-range"],
        type_parser=argvalidators.PositiveIntRange.type_parser,
        default=(3, 25),
        metavar=argvalidators.PositiveIntRange.METAVAR,
        help="Range for the speed of the falling rain as determined by the delay between rows. Actual delay is randomly selected from the range.",
    )  # type: ignore[assignment]
    "tuple[int, int] : Speed of the falling rain as determined by the delay between rows. Actual delay is randomly selected from the range."

    rain_column_delay_range: tuple[int, int] = ArgField(
        cmd_name=["--rain-column-delay-range"],
        type_parser=argvalidators.PositiveIntRange.type_parser,
        default=(5, 15),
        metavar=argvalidators.PositiveIntRange.METAVAR,
        help="Range of frames to wait between adding new rain columns.",
    )  # type: ignore[assignment]
    "tuple[int, int] : Range of frames to wait between adding new rain columns."

    rain_time: int = ArgField(
        cmd_name="--rain-time",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=15,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Time, in seconds, to display the rain effect before transitioning to the input text.",
    )  # type: ignore[assignment]
    "int : Time, in seconds, to display the rain effect before transitioning to the input text."

    symbol_swap_chance: float = ArgField(
        cmd_name="--symbol-swap-chance",
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=0.005,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Chance of swapping a character's symbol on each tick.",
    )  # type: ignore[assignment]
    "float : Chance of swapping a character's symbol on each tick."

    color_swap_chance: float = ArgField(
        cmd_name="--color-swap-chance",
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=0.001,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Chance of swapping a character's color on each tick.",
    )  # type: ignore[assignment]
    "float : Chance of swapping a character's color on each tick."

    resolve_delay: int = ArgField(
        cmd_name="--resolve-delay",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=5,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Number of frames to wait between resolving the next group of characters. This is used to adjust the speed of the final resolve phase.",
    )  # type: ignore[assignment]
    "int : Number of frames to wait between resolving the next group of characters. This is used to adjust the speed of the final resolve phase."

    final_gradient_stops: tuple[Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("92be92"), Color("336b33")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] | int = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_frames: int = ArgField(
        cmd_name="--final-gradient-frames",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=5,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step. Increase to slow down the gradient animation.",
    )  # type: ignore[assignment]
    "int : Number of frames to display each gradient step. Increase to slow down the gradient animation."

    final_gradient_direction: Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=Gradient.Direction.RADIAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "Gradient.Direction : Direction of the final gradient."

    @classmethod
    def get_effect_class(cls):
        return Matrix


class MatrixIterator(BaseEffectIterator[MatrixConfig]):
    class RainColumn:
        def __init__(
            self, characters: list[EffectCharacter], terminal: Terminal, config: MatrixConfig, rain_colors: Gradient
        ) -> None:
            self.terminal = terminal
            self.config = config
            self.characters: list[EffectCharacter] = characters
            self.pending_characters: list[EffectCharacter] = []
            self.matrix_symbols: tuple[str, ...] = config.rain_symbols
            self.rain_colors = rain_colors
            self.column_drop_chance = 0.08
            self.setup_column("rain")

        def setup_column(self, phase: str) -> None:
            self.pending_characters.clear()
            self.phase = phase
            for character in self.characters:
                self.terminal.set_character_visibility(character, False)
                self.pending_characters.append(character)
                character.motion.current_coord = character.input_coord
            self.visible_characters: list[EffectCharacter] = []
            if self.phase == "fill":
                self.base_rain_fall_delay = random.randint(
                    max(self.config.rain_fall_delay_range[0] // 3, 1), max(self.config.rain_fall_delay_range[1] // 3, 1)
                )
            else:
                self.base_rain_fall_delay = random.randint(
                    self.config.rain_fall_delay_range[0], self.config.rain_fall_delay_range[1]
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
            if not self.visible_characters:
                return
            popped_char = self.visible_characters.pop(0)
            self.terminal.set_character_visibility(popped_char, False)
            if len(self.visible_characters) > 1:
                self.fade_last_character()

        def drop_column(self) -> None:
            out_of_canvas = []
            for character in self.visible_characters:
                character.motion.current_coord = Coord(
                    character.motion.current_coord.column, character.motion.current_coord.row - 1
                )
                if character.motion.current_coord.row < self.terminal.canvas.bottom:
                    self.terminal.set_character_visibility(character, False)
                    out_of_canvas.append(character)
            self.visible_characters = [char for char in self.visible_characters if char not in out_of_canvas]

        def fade_last_character(self) -> None:
            darker_color = Animation.adjust_color_brightness(random.choice(self.rain_colors[-3:]), 0.65)  # type: ignore
            self.visible_characters[0].animation.set_appearance(
                self.visible_characters[0].animation.current_character_visual.symbol, fg_color=darker_color
            )

        def resolve_char(self) -> EffectCharacter:
            random_char = self.visible_characters.pop(random.randint(0, len(self.visible_characters) - 1))
            return random_char

        def tick(self) -> None:
            if not self.active_rain_fall_delay:
                if self.pending_characters:
                    next_char = self.pending_characters.pop(0)
                    next_char.animation.set_appearance(
                        random.choice(self.matrix_symbols), fg_color=self.config.highlight_color
                    )
                    previous_character = self.visible_characters[-1] if self.visible_characters else None
                    # if there is a previous character, remove the highlight
                    if previous_character:
                        previous_character.animation.set_appearance(
                            previous_character.animation.current_character_visual.symbol,
                            fg_color=random.choice(self.rain_colors),
                        )
                    self.terminal.set_character_visibility(next_char, True)
                    self.visible_characters.append(next_char)

                # if no pending characters, but still visible characters, trim the column
                # unless the column is the full height of the canvas, then respect the hold
                # time before trimming
                else:
                    if self.visible_characters:
                        # adjust the bottom character color to remove the lightlight.
                        # always do this on the first hold frame, then
                        # randomly adjust the bottom character's color
                        # this is separately handled from the rest to prevent the
                        # highlight color from being replaced before appropriate
                        if (
                            self.visible_characters[-1].animation.current_character_visual.fg_color
                            == self.config.highlight_color
                        ):
                            self.visible_characters[-1].animation.set_appearance(
                                self.visible_characters[-1].animation.current_character_visual.symbol,
                                fg_color=random.choice(self.rain_colors),
                            )

                        if self.hold_time:
                            self.hold_time -= 1
                        else:
                            if self.phase == "rain":
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
                else:
                    next_color = character.animation.current_character_visual.fg_color
                character.animation.set_appearance(next_symbol, fg_color=next_color)

    def __init__(self, effect: Matrix) -> None:
        super().__init__(effect)
        self.pending_columns: list[MatrixIterator.RainColumn] = []
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.active_columns: list[MatrixIterator.RainColumn] = []
        self.full_columns: list[MatrixIterator.RainColumn] = []
        self.rain_colors = Gradient(*self.config.rain_color_gradient, steps=6)
        self.column_delay = 0
        self.resolve_delay = self.config.resolve_delay
        self.phase = "rain"
        self.build()
        self.rain_start = time.time()

    def build(self) -> None:
        final_gradient = Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.text_bottom,
            self.terminal.canvas.text_top,
            self.terminal.canvas.text_left,
            self.terminal.canvas.text_right,
            self.config.final_gradient_direction,
        )
        for character in self.terminal.get_characters():
            resolve_scn = character.animation.new_scene(id="resolve")
            for color in Gradient(self.config.highlight_color, final_gradient_mapping[character.input_coord], steps=8):
                resolve_scn.add_frame(character.input_symbol, self.config.final_gradient_frames, fg_color=color)

        for column_chars in self.terminal.get_characters_grouped(
            self.terminal.CharacterGroup.COLUMN_LEFT_TO_RIGHT, outer_fill_chars=True, inner_fill_chars=True
        ):
            column_chars.reverse()
            self.pending_columns.append(
                MatrixIterator.RainColumn(column_chars, self.terminal, self.config, self.rain_colors)
            )
        random.shuffle(self.pending_columns)

    def __next__(self) -> str:
        if self.phase == "rain" or self.phase == "fill":
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
                        self.config.rain_column_delay_range[0], self.config.rain_column_delay_range[1]
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
                    else:
                        if not column.visible_characters:
                            column.setup_column(self.phase)
                            self.pending_columns.append(column)

            self.active_columns = [column for column in self.active_columns if column.visible_characters]
            if self.phase == "fill":
                if not self.pending_columns and all(
                    [(not column.pending_characters and column.phase == "fill") for column in self.active_columns]
                ):
                    self.phase = "resolve"
                    self.active_columns.clear()

            if self.phase == "rain" and self.config.rain_time > 0:
                if time.time() - self.rain_start > self.config.rain_time:
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
                                    next_char.animation.activate_scene(next_char.animation.query_scene("resolve"))
                                    self.active_characters.add(next_char)
                                else:
                                    self.terminal.set_character_visibility(next_char, False)
                        self.resolve_delay = self.config.resolve_delay
                    else:
                        self.resolve_delay -= 1

            self.full_columns = [column for column in self.full_columns if column.visible_characters]

        if self.full_columns or self.active_columns or self.active_characters:
            self.update()
            return self.frame
        else:
            raise StopIteration


class Matrix(BaseEffect[MatrixConfig]):
    """Matrix digital rain effect.

    Attributes:
        effect_config (MatrixConfig): Configuration for the Matrix effect.
        terminal_config (TerminalConfig): Configuration for the terminal."""

    _config_cls = MatrixConfig
    _iterator_cls = MatrixIterator

    def __init__(self, input_data: str) -> None:
        """Initialize the effect with the provided input data.

        Args:
            input_data (str): The input data to use for the effect."""
        super().__init__(input_data)
