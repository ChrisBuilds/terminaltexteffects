"""A module for managing the terminal state and output.

Classes:
    TerminalConfig: Configuration for the terminal.
    Terminal: A class for managing the terminal state and output.
"""

from __future__ import annotations

import random
import shutil
import sys
import time
import typing
import weakref
from bisect import bisect_left
from contextlib import suppress
from copy import deepcopy
from dataclasses import FrozenInstanceError, dataclass
from operator import attrgetter
from typing import Literal

from terminaltexteffects.engine import canvas as canvas_module
from terminaltexteffects.engine.base_character import EffectCharacter
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.terminal_input import ParsedCharacter, VirtualScreenParser
from terminaltexteffects.utils import ansitools, argutils
from terminaltexteffects.utils.argutils import CharacterGroup, CharacterSort, ColorSort
from terminaltexteffects.utils.exceptions import (
    InvalidCharacterCoordinateError,
    InvalidCharacterError,
    InvalidCharacterGroupError,
    InvalidCharacterSortError,
    InvalidCharacterVisibilityError,
    InvalidColorSortError,
    TerminalOutputActiveError,
    TerminalOutputNotPreparedError,
)
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.graphics import Color
from terminaltexteffects.utils.terminal_text import get_symbol_cell_width

_CHARACTER_ID_KEY = attrgetter("_character_id")
_LAYER_KEY = attrgetter("_layer")


@dataclass
class TerminalConfig(BaseConfig):
    """Configuration for the terminal.

    Attributes:
        tab_width (int): Number of spaces to use for a tab character.
        xterm_colors (bool): Convert any colors specified in RGB hex to the closest XTerm-256 color.
        no_color (bool): Disable all colors in the effect.
        terminal_background_color (Color): Background color of the terminal used by effects that depend on it.
        existing_color_handling (Literal['always','dynamic','ignore']): Specify handling of existing ANSI SGR color
            sequences in the input data. Supported input colors include 3-bit, 4-bit, 8-bit, and 24-bit
            foreground/background sequences. 'always' will always use the input colors, ignoring any effect specific
            colors. 'dynamic' will leave it to the effect implementation to apply input colors. 'ignore' will ignore
            the colors in the input data. Default is 'ignore'.
        wrap_text (bool): Wrap text wider than the canvas width.
        frame_rate (int): Target frame rate for the animation in frames per second. Set to 0 to disable frame
            rate limiting.
        canvas_width (int): Canvas width, set to an integer > 0 to use a specific dimension, if set to 0 the canvas
            width is detected automatically based on the terminal device, if set to -1 the canvas width is based on
            the input data width.
        canvas_height (int): Canvas height, set to an integer > 0 to use a specific dimension, if set to 0 the canvas
            height is detected automatically based on the terminal device, if set to -1 the canvas height is
            based on the input data height.
        anchor_canvas (Literal['sw','s','se','e','ne','n','nw','w','c']): Anchor point for the Canvas. The Canvas will
            be anchored in the terminal to the location corresponding to the cardinal/diagonal direction.
            Defaults to 'sw'.
        anchor_text (Literal['n','ne','e','se','s','sw','w','nw','c']): Anchor point for the text within the Canvas.
            Input text will be anchored in the Canvas to the location corresponding to the cardinal/diagonal
            direction. Defaults to 'sw'.
        ignore_terminal_dimensions (bool): Ignore the terminal dimensions and utilize the full Canvas beyond the extents
            of the terminal. Useful for sending frames to another output handler.
        reuse_canvas (bool): Do not create new rows at the start of the effect. The cursor will be restored to the
            position of the previous canvas.
        no_eol (bool): Suppress the trailing newline emitted when an effect animation completes.
        no_restore_cursor (bool): Do not restore cursor visibility when an effect animation completes.

    """

    _is_frozen: typing.ClassVar[bool] = False

    def __setattr__(self, name: str, value: typing.Any) -> None:
        """Normalize assignments until this config becomes a terminal snapshot."""
        if self._is_frozen:
            message = f"cannot assign to field {name!r} on a terminal configuration snapshot"
            raise FrozenInstanceError(message)
        super().__setattr__(name, value)

    def _freeze(self) -> None:
        """Prevent mutation after the configuration is installed on a `Terminal`."""
        object.__setattr__(self, "_is_frozen", True)

    tab_width: int = argutils.ArgSpec(
        name="--tab-width",
        type=argutils.PositiveInt.type_parser,
        metavar=argutils.PositiveInt.METAVAR,
        default=4,
        help="Number of spaces to use for a tab character.",
    )  # pyright: ignore[reportAssignmentType]
    "int : Number of spaces to use for a tab character."

    xterm_colors: bool = argutils.ArgSpec(
        name="--xterm-colors",
        default=False,
        action="store_true",
        help="Convert any colors specified in 24-bit RGB hex to the closest 8-bit XTerm-256 color.",
    )  # pyright: ignore[reportAssignmentType]
    "bool : Convert any colors specified in 24-bit RGB hex to the closest 8-bit XTerm-256 color."

    no_color: bool = argutils.ArgSpec(
        name="--no-color",
        default=False,
        action="store_true",
        help="Disable all colors in the effect.",
    )  # pyright: ignore[reportAssignmentType]
    "bool : Disable all colors in the effect."

    terminal_background_color: Color = argutils.ArgSpec(
        name="--terminal-background-color",
        type=argutils.ColorArg.type_parser,
        default=Color("#000000"),
        metavar=argutils.ColorArg.METAVAR,
        help=(
            "The background color of your terminal. "
            "Used to determine the appropriate color for fade-in/out within effects."
        ),
    )  # type: ignore[assignment]
    "Color: User-defined background color of the terminal."

    existing_color_handling: Literal["always", "dynamic", "ignore"] = argutils.ArgSpec(
        name="--existing-color-handling",
        default="ignore",
        choices=["always", "dynamic", "ignore"],
        help=(
            "Specify handling of existing ANSI SGR color sequences in the input data. Supported input colors include "
            "3-bit, 4-bit, 8-bit, and 24-bit foreground/background sequences. 'always' will always use the input "
            "colors, ignoring any effect specific colors. 'dynamic' will leave it to the effect implementation to "
            "apply input colors. 'ignore' will ignore the colors in the input data. Default is 'ignore'."
        ),
    )  # pyright: ignore[reportAssignmentType]
    (
        "Literal['always','dynamic','ignore'] : Specify handling of existing ANSI SGR color sequences in the input "
        "data. Supported input colors include 3-bit, 4-bit, 8-bit, and 24-bit foreground/background sequences. "
        "'always' will always use the input colors, ignoring any effect specific colors. 'dynamic' will leave it to "
        "the effect implementation to apply input colors. 'ignore' will ignore the colors in the input data. "
        "Default is 'ignore'."
    )

    wrap_text: bool = argutils.ArgSpec(
        name="--wrap-text",
        default=False,
        action="store_true",
        help="Wrap text wider than the canvas width.",
    )  # pyright: ignore[reportAssignmentType]
    "bool : Wrap text wider than the canvas width."

    frame_rate: int = argutils.ArgSpec(
        name="--frame-rate",
        type=argutils.NonNegativeInt.type_parser,
        default=60,
        help=(
            "Target frame rate for the animation in frames per second. Set to 0 to disable frame rate limiting. "
            "Defaults to 60."
        ),
    )  # type: ignore[assignment]

    "int : Target frame rate for the animation in frames per second. Set to 0 to disable frame rate limiting."

    canvas_width: int = argutils.ArgSpec(
        name="--canvas-width",
        metavar=argutils.CanvasDimension.METAVAR,
        type=argutils.CanvasDimension.type_parser,
        default=-1,
        help=(
            "Canvas width, set to an integer > 0 to use a specific dimension, use 0 to match the terminal width, "
            "or use -1 to match the input text width. Defaults to -1."
        ),
    )  # pyright: ignore[reportAssignmentType]
    (
        "int : Canvas width, set to an integer > 0 to use a specific dimension, if set to 0 the canvas width is "
        "detected automatically based on the terminal device, if set to -1 the canvas width is based on "
        "the input data width. Defaults to -1."
    )

    canvas_height: int = argutils.ArgSpec(
        name="--canvas-height",
        metavar=argutils.CanvasDimension.METAVAR,
        type=argutils.CanvasDimension.type_parser,
        default=-1,
        help=(
            "Canvas height, set to an integer > 0 to use a specific dimension, use 0 to match the terminal "
            "height, or use -1 to match the input text height. Defaults to -1."
        ),
    )  # pyright: ignore[reportAssignmentType]
    (
        "int : Canvas height, set to an integer > 0 to use a specific dimension, if set to 0 the canvas height "
        "is detected automatically based on the terminal device, if set to -1 the canvas height is "
        "based on the input data height. Defaults to -1."
    )

    anchor_canvas: Literal["sw", "s", "se", "e", "ne", "n", "nw", "w", "c"] = argutils.ArgSpec(
        name="--anchor-canvas",
        choices=["sw", "s", "se", "e", "ne", "n", "nw", "w", "c"],
        default="sw",
        help=(
            "Anchor point for the canvas. The canvas will be anchored in the terminal to the location "
            "corresponding to the cardinal/diagonal direction. Defaults to 'sw'."
        ),
    )  # pyright: ignore[reportAssignmentType]
    (
        "Literal['sw','s','se','e','ne','n','nw','w','c'] : Anchor point for the canvas. The canvas will be "
        "anchored in the terminal to the location corresponding to the cardinal/diagonal direction. Defaults to 'sw'."
    )

    anchor_text: Literal["n", "ne", "e", "se", "s", "sw", "w", "nw", "c"] = argutils.ArgSpec(
        name="--anchor-text",
        choices=["n", "ne", "e", "se", "s", "sw", "w", "nw", "c"],
        default="sw",
        help=(
            "Anchor point for the text within the Canvas. Input text will be anchored in the Canvas to "
            "the location corresponding to the cardinal/diagonal direction. Defaults to 'sw'."
        ),
    )  # pyright: ignore[reportAssignmentType]
    (
        "Literal['n','ne','e','se','s','sw','w','nw','c'] : Anchor point for the text within the Canvas. "
        "Input text will be anchored in the Canvas to the location corresponding to the cardinal/diagonal direction. "
        "Defaults to 'sw'."
    )

    ignore_terminal_dimensions: bool = argutils.ArgSpec(
        name="--ignore-terminal-dimensions",
        default=False,
        action="store_true",
        help=(
            "Ignore the terminal dimensions and utilize the full Canvas beyond the extents of the terminal. "
            "Useful for sending frames to another output handler."
        ),
    )  # pyright: ignore[reportAssignmentType]
    (
        "bool : Ignore the terminal dimensions and utilize the full Canvas beyond the extents of the terminal. "
        "Useful for sending frames to another output handler."
    )

    reuse_canvas: bool = argutils.ArgSpec(
        name="--reuse-canvas",
        default=False,
        action="store_true",
        help=(
            "Do not create new rows at the start of the effect. The cursor will be moved up the number of rows "
            "present in the input text in an attempt to re-use the canvas. This option works best when used in "
            "a shell script. If used interactively with prompts between runs, the result is unpredictable."
        ),
    )  # pyright: ignore[reportAssignmentType]
    (
        "bool: Do not create new rows at the start of the effect. The cursor will be moved up the number of rows "
        "present in the input text in an attempt to re-use the canvas. This option works best when used in "
        "a shell script. If used interactively with prompts between runs, the result is unpredictable."
    )

    no_eol: bool = argutils.ArgSpec(
        name="--no-eol",
        default=False,
        action="store_true",
        help=("Suppress the trailing newline emitted when an effect animation completes."),
    )  # pyright: ignore[reportAssignmentType]
    ("bool : Suppress the trailing newline emitted when an effect animation completes. ")

    no_restore_cursor: bool = argutils.ArgSpec(
        name="--no-restore-cursor",
        default=False,
        action="store_true",
        help=("Do not restore cursor visibility after the effect."),
    )  # pyright: ignore[reportAssignmentType]
    ("bool : Do not restore cursor visibility after the effect.")


class Terminal:
    """A class for managing the terminal state and output.

    The terminal tracks input characters, fill characters, added characters, and the
    currently visible rendered state for the active canvas.

    Attributes:
        config (TerminalConfig): Immutable construction-time configuration snapshot. To apply different settings,
            construct a new `Terminal` from a mutable `TerminalConfig`.
        canvas (Canvas): The canvas in the terminal.
        character_by_input_coord (dict[Coord, EffectCharacter]): Mapping of input-character leading coordinates and
            fill characters keyed by canvas coordinates. Accessing the mapping materializes any deferred fill
            characters. Characters created with `add_character()` are tracked separately.
        terminal_state (list[str]): Internal row-by-row representation of the currently visible terminal output.
        visible_top (int): Top visible row within the terminal after canvas anchoring is applied.
        visible_bottom (int): Bottom visible row within the terminal after canvas anchoring is applied.
        visible_right (int): Rightmost visible column within the terminal after canvas anchoring is applied.
        visible_left (int): Leftmost visible column within the terminal after canvas anchoring is applied.

    Methods:
        get_piped_input:
            Gets the piped input from stdin.
        prep_canvas:
            Prepares the terminal for the effect by adding empty lines and hiding the cursor.
        restore_cursor:
            Restores the cursor visibility.
        get_characters:
            Get a list of all EffectCharacters in the terminal with an optional sort.
        get_characters_grouped:
            Get a list of all EffectCharacters grouped by the specified CharacterGroup grouping.
        get_character_by_input_coord:
            Get an EffectCharacter by its input coordinates.
        prepare_character_graph:
            Materialize fill characters and cardinal neighbor relationships.
        set_character_visibility:
            Set the visibility of a character.
        get_formatted_output_string:
            Get the formatted output string based on the current terminal state.
        print:
            Prints the current terminal state to stdout while preserving the cursor position.

    """

    _active_output_terminal: typing.ClassVar[weakref.ReferenceType[Terminal] | None] = None

    def __init__(self, input_data: str, config: TerminalConfig | None = None) -> None:
        """Initialize the Terminal.

        Args:
            input_data (str): The input data to be displayed in the terminal. Empty input produces an empty text
                region on a minimal one-cell canvas.
            config (TerminalConfig, optional): Configuration copied into an immutable construction-time snapshot.
                Later mutations to the caller's configuration do not affect this terminal. Defaults to None.

        """
        self.config = deepcopy(config) if config is not None else TerminalConfig._build_config()
        self.config._freeze()
        self._character_ownership_token = weakref.ref(self)
        self._output_prepared = False
        self._next_character_id = 0
        self._input_parser = VirtualScreenParser(tab_width=self.config.tab_width)
        self._preprocessed_character_columns: dict[EffectCharacter, int] = {}
        self._preprocessed_line_widths: list[int] = []
        self._preprocessed_character_lines = self._preprocess_input_data(input_data)
        self._wrapped_character_lines: list[list[EffectCharacter]] | None = None
        self._wrapped_character_line_widths: list[int] | None = None
        self._wrapped_character_columns: dict[EffectCharacter, int] = {}
        self._wrapped_character_lines_width: int | None = None
        self._terminal_width, self._terminal_height = self._get_terminal_dimensions()
        self.canvas = canvas_module.Canvas(*self._get_canvas_dimensions())
        if not self.config.ignore_terminal_dimensions:
            self.canvas_column_offset, self.canvas_row_offset = self._calc_canvas_offsets()
        else:
            self.canvas_column_offset = self.canvas_row_offset = 0
            self._terminal_width = self.canvas.right
            self._terminal_height = self.canvas.top
        # the visible_* attributes are used to determine which characters are visible on the terminal
        self.visible_top = min(self.canvas.top + self.canvas_row_offset, self._terminal_height)
        self.visible_bottom = max(self.canvas.bottom + self.canvas_row_offset, 1)
        self.visible_right = min(
            self.canvas.right + self.canvas_column_offset,
            self._terminal_width,
        )
        self.visible_left = max(self.canvas.left + self.canvas_column_offset, 1)
        self._input_characters = [
            character
            for character in self._setup_input_characters()
            if character.input_coord.row <= self.canvas.top and character.input_coord.column <= self.canvas.right
        ]
        self._input_colors_frequency: dict[Color, int] = {}
        for character in self._input_characters:
            for color in (character.animation.input_fg_color, character.animation.input_bg_color):
                if color is not None:
                    self._input_colors_frequency[color] = self._input_colors_frequency.get(color, 0) + 1
        self._added_characters: list[EffectCharacter] = []
        self._character_by_input_coord: dict[Coord, EffectCharacter] = {
            (character.input_coord): character for character in self._input_characters
        }
        self._input_character_continuations: dict[Coord, EffectCharacter] = {
            Coord(character.input_coord.column + offset, character.input_coord.row): character
            for character in self._input_characters
            for offset in range(1, character.animation.current_character_visual.cell_width)
        }
        self._inner_fill_characters: list[EffectCharacter] = []
        self._outer_fill_characters: list[EffectCharacter] = []
        self._fill_characters_materialized = False
        self._character_neighbors_initialized = False
        self._character_by_occupied_coord = dict(self._character_by_input_coord)
        self._character_by_occupied_coord.update(self._input_character_continuations)
        occupied_cell_indexes = [
            (coord.row - self.canvas.bottom) * self.canvas.width + (coord.column - self.canvas.left)
            for coord in self._character_by_occupied_coord
            if self.canvas.coord_is_in_canvas(coord)
        ]
        self._input_occupied_cell_indexes = tuple(sorted(occupied_cell_indexes))
        self._fill_character_id_start = self._next_character_id
        self._next_character_id += self.canvas.width * self.canvas.height - len(self._input_occupied_cell_indexes)
        self._initialize_render_state()
        self._frame_rate = self.config.frame_rate
        self._last_time_printed = time.monotonic()
        self._update_terminal_state()

    def _initialize_render_state(self) -> None:
        """Initialize visible-character ordering and reusable blank output rows."""
        self._visible_characters: set[EffectCharacter] = set()
        self._visible_characters_by_id: list[EffectCharacter] = []
        self._visible_character_layer_counts: dict[int, int] = {}
        self._visible_characters_by_layer: list[EffectCharacter] = []
        self._visible_character_order_dirty = False
        self._blank_row = " " * self.visible_right
        self._blank_terminal_state = [self._blank_row] * self.visible_top

    def _build_input_character(self, parsed_character: ParsedCharacter, character_id_offset: int) -> EffectCharacter:
        """Allocate one terminal-owned character from parser output."""
        character = EffectCharacter(
            character_id_offset + parsed_character.character_id,
            parsed_character.symbol,
            0,
            0,
        )
        character._terminal_owner_token = self._character_ownership_token
        character.animation.input_fg_color = parsed_character.fg_color
        character.animation.input_bg_color = parsed_character.bg_color
        character.animation.input_bold = parsed_character.bold
        character.animation.no_color = self.config.no_color
        character.animation.use_xterm_colors = self.config.xterm_colors
        character.animation.existing_color_handling = self.config.existing_color_handling
        character.uses_input_preexisting_colors = True
        if character.animation.existing_color_handling == "always":
            character.animation.set_appearance(character.input_symbol)
        return character

    def _preprocess_input_data(self, input_data: str) -> list[list[EffectCharacter]]:
        """Parse input and allocate the retained terminal-owned characters."""
        parsed_input = self._input_parser.parse(input_data)
        character_id_offset = self._next_character_id
        character_lines: list[list[EffectCharacter]] = []
        character_columns: dict[EffectCharacter, int] = {}
        for parsed_row in parsed_input.character_rows:
            character_line: list[EffectCharacter] = []
            for parsed_character in parsed_row:
                character = self._build_input_character(parsed_character, character_id_offset)
                character_line.append(character)
                character_columns[character] = parsed_character.column
            character_lines.append(character_line)

        self._next_character_id += parsed_input.character_id_count
        self._preprocessed_character_columns = character_columns
        self._preprocessed_line_widths = list(parsed_input.line_widths)
        return character_lines

    def _calc_canvas_offsets(self) -> tuple[int, int]:
        """Calculate terminal-space offsets for the anchored canvas.

        The returned column and row offsets position the canvas within the available
        terminal area according to `config.anchor_canvas`. These offsets are later
        applied when determining visible bounds and when rendering character positions.

        Returns:
            tuple[int, int]: Canvas column offset and row offset.

        """
        canvas_column_offset = canvas_row_offset = 0
        if self.config.anchor_canvas in ("s", "n", "c"):
            canvas_column_offset = (self._terminal_width - self.canvas.width) // 2
        elif self.config.anchor_canvas in ("se", "e", "ne"):
            canvas_column_offset = self._terminal_width - self.canvas.width
        if self.config.anchor_canvas in ("w", "e", "c"):
            canvas_row_offset = (self._terminal_height - self.canvas.height) // 2
        elif self.config.anchor_canvas in ("nw", "n", "ne"):
            canvas_row_offset = self._terminal_height - self.canvas.height
        return canvas_column_offset, canvas_row_offset

    def _get_canvas_dimensions(self) -> tuple[int, int]:
        """Determine the canvas dimensions from terminal config and input geometry.

        Explicit positive canvas dimensions take precedence. A configured value of `0`
        uses the terminal dimension, while `-1` derives the dimension from the input
        text, subject to terminal limits unless `ignore_terminal_dimensions` is enabled.
        When `wrap_text` is enabled, canvas height is based on the wrapped input lines
        for the selected width.

        Returns:
            tuple[int, int]: Canvas height and width.

        """
        if self.config.canvas_width > 0:
            canvas_width = self.config.canvas_width
        elif self.config.canvas_width == 0:
            canvas_width = self._terminal_width
        else:
            input_width = max(self._preprocessed_line_widths)
            if self.config.ignore_terminal_dimensions:
                canvas_width = input_width
            else:
                canvas_width = min(self._terminal_width, input_width)
        if self.config.canvas_height > 0:
            canvas_height = self.config.canvas_height
        elif self.config.canvas_height == 0:
            canvas_height = self._terminal_height
        else:
            input_height = len(self._preprocessed_character_lines)
            if self.config.wrap_text:
                input_height = len(self._get_wrapped_character_lines(canvas_width))
            if self.config.ignore_terminal_dimensions:
                canvas_height = input_height
            else:
                canvas_height = min(self._terminal_height, input_height)

        return canvas_height, canvas_width

    def _get_terminal_dimensions(self) -> tuple[int, int]:
        """Get the terminal dimensions.

        Use `shutil.get_terminal_size()` to get terminal width and height. If that call
        raises `OSError`, return the fallback size `(80, 24)`.

        Returns:
            tuple[int, int]: Terminal width and height.

        """
        try:
            terminal_width, terminal_height = shutil.get_terminal_size()
        except OSError:
            # If the terminal size cannot be determined, return default values
            return 80, 24
        return terminal_width, terminal_height

    @staticmethod
    def get_piped_input() -> str:
        """Return piped input from `stdin`.

        If `stdin` is attached to a TTY, return an empty string. Otherwise, read and
        return the full contents of `stdin`.

        Returns:
            str: The piped input, or an empty string when running interactively.

        """
        if sys.stdin.isatty():
            return ""
        return sys.stdin.read()

    def _wrap_lines(
        self,
        lines: list[list[EffectCharacter]],
        width: int,
    ) -> list[list[EffectCharacter]]:
        """Wrap the given lines of text to fit within the width of the canvas.

        Args:
            lines (list[list[EffectCharacter]]): The lines of text to be wrapped.
            width (int): The maximum length of a line.

        Returns:
            list[list[EffectCharacter]]: The wrapped lines of text.

        """
        wrapped_lines = []
        wrapped_line_widths = []
        line_widths = (
            self._preprocessed_line_widths
            if lines is self._preprocessed_character_lines
            else [
                max(
                    (
                        self._preprocessed_character_columns[character]
                        + character.animation.current_character_visual.cell_width
                        for character in line
                    ),
                    default=0,
                )
                for line in lines
            ]
        )
        wrapped_character_columns: dict[EffectCharacter, int] = {}
        for line, line_width in zip(lines, line_widths):
            placements: list[tuple[int, int, EffectCharacter]] = []
            inserted_padding = 0
            for character in line:
                logical_column = self._preprocessed_character_columns[character]
                adjusted_column = logical_column + inserted_padding
                character_width = character.animation.current_character_visual.cell_width
                column_in_chunk = adjusted_column % width
                if character_width <= width and column_in_chunk + character_width > width:
                    inserted_padding += width - column_in_chunk
                    adjusted_column = logical_column + inserted_padding
                    column_in_chunk = 0
                chunk_index = adjusted_column // width
                placements.append((chunk_index, column_in_chunk, character))
                wrapped_character_columns[character] = column_in_chunk
            adjusted_line_width = line_width + inserted_padding
            wrapped_line_count = max((adjusted_line_width + width - 1) // width, 1)
            line_chunks = [[] for _ in range(wrapped_line_count)]
            for chunk_index, _, character in placements:
                line_chunks[chunk_index].append(character)
            wrapped_lines.extend(line_chunks)
            wrapped_line_widths.extend(
                min(width, max(adjusted_line_width - (chunk_index * width), 0))
                for chunk_index in range(wrapped_line_count)
            )
        self._wrapped_character_columns = wrapped_character_columns
        self._wrapped_character_line_widths = wrapped_line_widths
        return wrapped_lines

    def _get_wrapped_character_lines(self, width: int) -> list[list[EffectCharacter]]:
        """Return cached wrapped input rows for the given canvas width."""
        if self._wrapped_character_lines is None or self._wrapped_character_lines_width != width:
            self._wrapped_character_lines = self._wrap_lines(self._preprocessed_character_lines, width)
            self._wrapped_character_lines_width = width
        return self._wrapped_character_lines

    def _setup_input_characters(self) -> list[EffectCharacter]:
        """Set up the input characters discovered during preprocessing.

        Characters are positioned based on row/column coordinates relative to the anchor point in the Canvas.
        Space characters from the input are excluded from the returned input-character
        list and are instead represented by fill characters when the canvas is populated.

        Coordinates are relative to the cursor row position at the time of execution. 1,1 is the bottom left
        corner of the row above the cursor.

        Returns:
            list[EffectCharacter]: list of EffectCharacter objects

        """
        formatted_lines = (
            self._get_wrapped_character_lines(self.canvas.right)
            if self.config.wrap_text
            else self._preprocessed_character_lines
        )
        input_height = len(formatted_lines)
        input_characters: list[EffectCharacter] = []
        input_cells: list[tuple[Coord, int]] = []
        for row, line in enumerate(formatted_lines):
            for character in line:
                logical_column = self._preprocessed_character_columns[character]
                column = (
                    self._wrapped_character_columns[character] + 1
                    if self.config.wrap_text
                    else logical_column + 1
                )
                if character._input_symbol != " " or any(
                    (character.animation.input_fg_color, character.animation.input_bg_color),
                ):
                    input_characters.append(character)
                    input_cells.append(
                        (
                            Coord(column, input_height - row),
                            character.animation.current_character_visual.cell_width,
                        ),
                    )

        layout = self.canvas.layout_text(input_cells, self.config.anchor_text)
        anchored_characters: list[EffectCharacter] = []
        for placement in layout.placements:
            character = input_characters[placement.source_index]
            character._set_input_coord(placement.coord)
            anchored_characters.append(character)
        return anchored_characters

    @property
    def character_by_input_coord(self) -> dict[Coord, EffectCharacter]:
        """Map input and fill coordinates to characters, materializing fills on access."""
        self._ensure_fill_characters()
        return self._character_by_input_coord

    def _get_or_create_fill_character(self, coord: Coord) -> EffectCharacter | None:
        """Return the character occupying `coord`, creating its fill character if needed."""
        if character := self._character_by_occupied_coord.get(coord):
            return character
        if not self.canvas.coord_is_in_canvas(coord):
            return None

        cell_index = (coord.row - self.canvas.bottom) * self.canvas.width + (coord.column - self.canvas.left)
        occupied_before = bisect_left(self._input_occupied_cell_indexes, cell_index)
        character_id = self._fill_character_id_start + cell_index - occupied_before
        fill_char = EffectCharacter(character_id, " ", coord.column, coord.row)
        fill_char._terminal_owner_token = self._character_ownership_token
        fill_char.is_fill_character = True
        fill_char.animation.no_color = self.config.no_color
        fill_char.animation.use_xterm_colors = self.config.xterm_colors
        fill_char.animation.existing_color_handling = self.config.existing_color_handling
        fill_char.uses_input_preexisting_colors = False
        self._character_by_input_coord[coord] = fill_char
        self._character_by_occupied_coord[coord] = fill_char
        if self.canvas.coord_is_in_text(coord):
            self._inner_fill_characters.append(fill_char)
        else:
            self._outer_fill_characters.append(fill_char)
        return fill_char

    def _ensure_fill_characters(self) -> None:
        """Materialize all fill characters in stable row-major ID order.

        Fill characters use a space as `input_symbol` and are inserted into
        `character_by_input_coord` for any canvas coordinate not already occupied by an
        input character. They are split into inner and outer fill characters based on
        whether the coordinate falls within the anchored text bounds.
        """
        if self._fill_characters_materialized:
            return
        for row in range(self.canvas.bottom, self.canvas.top + 1):
            for column in range(self.canvas.left, self.canvas.right + 1):
                coord = Coord(column, row)
                self._get_or_create_fill_character(coord)
        self._fill_characters_materialized = True

    def prepare_character_graph(self) -> None:
        """Materialize fill characters and cardinal neighbor relationships on demand."""
        if self._character_neighbors_initialized:
            return
        self._ensure_fill_characters()
        delta_map = {"north": (0, 1), "south": (0, -1), "west": (-1, 0)}
        for coord, char in self._character_by_input_coord.items():
            neighbors: dict[str, EffectCharacter | None] = {}
            for direction, delta in delta_map.items():
                neighbor_coord = Coord(column=coord.column + delta[0], row=coord.row + delta[1])
                neighbors[direction] = self._character_by_occupied_coord.get(neighbor_coord)
            east_coord = Coord(
                column=coord.column + char.animation.current_character_visual.cell_width,
                row=coord.row,
            )
            neighbors["east"] = self._character_by_occupied_coord.get(east_coord)
            char._neighbors = neighbors
        self._character_neighbors_initialized = True

    def add_character(self, symbol: str, coord: Coord) -> EffectCharacter:
        """Add a character to the terminal for printing.

        Used to create characters that are not in the input data.
        Added characters are stored in `_added_characters` and are not inserted into
        `character_by_input_coord`. As a result, they are not returned by
        `get_character_by_input_coord()` and are not included in the neighbor map built
        from `character_by_input_coord`.

        Args:
            symbol (str): symbol to add
            coord (Coord): set character's input coordinates

        Returns:
            EffectCharacter: the character that was added

        Raises:
            InvalidCharacterCoordinateError: If `coord` is not a `Coord` containing integer values.
            InvalidSymbolError: If `symbol` does not contain one independently printable Unicode code point.

        """
        get_symbol_cell_width(symbol)
        if not isinstance(coord, Coord) or type(coord.column) is not int or type(coord.row) is not int:
            raise InvalidCharacterCoordinateError(coord)
        character = EffectCharacter(self._next_character_id, symbol, coord.column, coord.row)
        character._terminal_owner_token = self._character_ownership_token
        character.animation.no_color = self.config.no_color
        character.animation.use_xterm_colors = self.config.xterm_colors
        character.animation.existing_color_handling = self.config.existing_color_handling
        character.uses_input_preexisting_colors = False

        self._added_characters.append(character)
        self._next_character_id += 1
        return character

    def get_input_colors(self, sort: ColorSort = ColorSort.MOST_TO_LEAST) -> list[Color]:
        """Get colors used by retained input characters with an optional sort.

        Foreground and background occurrences are counted separately after cursor
        overwrites, text anchoring, and canvas clipping. Equal-frequency colors retain
        their first-appearance order unless random sorting is requested.

        Args:
            sort (ColorSort, optional): Sort order for the colors.
                Defaults to `ColorSort.MOST_TO_LEAST`.

        Raises:
            InvalidColorSortError: If an invalid sort option is provided.

        Returns:
            list[Color]: Colors used by input characters retained within the canvas.

        """
        if sort == ColorSort.MOST_TO_LEAST:
            return sorted(
                self._input_colors_frequency.keys(),
                key=lambda color: self._input_colors_frequency[color],
                reverse=True,
            )
        if sort == ColorSort.RANDOM:
            colors = list(self._input_colors_frequency.keys())
            random.shuffle(colors)
            return colors
        if sort == ColorSort.LEAST_TO_MOST:
            return sorted(
                self._input_colors_frequency.keys(),
                key=lambda color: self._input_colors_frequency[color],
            )
        raise InvalidColorSortError(sort)

    def _get_selected_characters(
        self,
        *,
        input_chars: bool,
        inner_fill_chars: bool,
        outer_fill_chars: bool,
        added_chars: bool,
    ) -> list[EffectCharacter]:
        """Collect requested character categories, materializing fills only when selected."""
        if inner_fill_chars or outer_fill_chars:
            self._ensure_fill_characters()
        all_characters: list[EffectCharacter] = []
        if input_chars:
            all_characters.extend(self._input_characters)
        if inner_fill_chars:
            all_characters.extend(self._inner_fill_characters)
        if outer_fill_chars:
            all_characters.extend(self._outer_fill_characters)
        if added_chars:
            all_characters.extend(self._added_characters)
        return all_characters

    def get_characters(
        self,
        *,
        input_chars: bool = True,
        inner_fill_chars: bool = False,
        outer_fill_chars: bool = False,
        added_chars: bool = False,
        sort: CharacterSort = CharacterSort.TOP_TO_BOTTOM_LEFT_TO_RIGHT,
    ) -> list[EffectCharacter]:
        """Get all selected `EffectCharacter` instances with an optional sort.

        Sorting uses each character's immutable input coordinate, not its current motion
        coordinate. Unlike `get_characters_grouped()`, this inventory includes selected
        added characters whose input coordinates are outside the canvas.

        The row-based outside/middle sorts order complete rows by their distance from
        the vertical midpoint of the selected rows. Rows equidistant from the midpoint
        are ordered top-first, and characters within each row remain left-to-right.

        Args:
            input_chars (bool, optional): whether to include input characters. Defaults to True.
            inner_fill_chars (bool, optional): whether to include inner fill characters. Defaults to False.
            outer_fill_chars (bool, optional): whether to include outer fill characters. Defaults to False.
            added_chars (bool, optional): whether to include added characters. Defaults to False.
            sort (CharacterSort, optional): order to sort the characters.
                Defaults to CharacterSort.TOP_TO_BOTTOM_LEFT_TO_RIGHT.

        Returns:
            list[EffectCharacter]: list of EffectCharacters in the terminal

        Raises:
            InvalidCharacterSortError: If an invalid sort option is provided.

        """
        all_characters = self._get_selected_characters(
            input_chars=input_chars,
            inner_fill_chars=inner_fill_chars,
            outer_fill_chars=outer_fill_chars,
            added_chars=added_chars,
        )

        # default sort TOP_TO_BOTTOM_LEFT_TO_RIGHT
        all_characters.sort(
            key=lambda character: (-character.input_coord.row, character.input_coord.column),
        )

        if sort is CharacterSort.RANDOM:
            random.shuffle(all_characters)

        elif sort in (
            CharacterSort.TOP_TO_BOTTOM_LEFT_TO_RIGHT,
            CharacterSort.BOTTOM_TO_TOP_RIGHT_TO_LEFT,
        ):
            if sort is CharacterSort.BOTTOM_TO_TOP_RIGHT_TO_LEFT:
                all_characters.reverse()

        elif sort in (
            CharacterSort.BOTTOM_TO_TOP_LEFT_TO_RIGHT,
            CharacterSort.TOP_TO_BOTTOM_RIGHT_TO_LEFT,
        ):
            all_characters.sort(
                key=lambda character: (character.input_coord.row, character.input_coord.column),
            )
            if sort is CharacterSort.TOP_TO_BOTTOM_RIGHT_TO_LEFT:
                all_characters.reverse()

        elif sort in (
            CharacterSort.OUTSIDE_ROW_TO_MIDDLE,
            CharacterSort.MIDDLE_ROW_TO_OUTSIDE,
        ):
            characters_by_row: dict[int, list[EffectCharacter]] = {}
            for character in all_characters:
                characters_by_row.setdefault(character.input_coord.row, []).append(character)
            if characters_by_row:
                row_midpoint_sum = min(characters_by_row) + max(characters_by_row)
                distance_sign = -1 if sort is CharacterSort.OUTSIDE_ROW_TO_MIDDLE else 1
                ordered_rows = sorted(
                    characters_by_row,
                    key=lambda row: (
                        distance_sign * abs((2 * row) - row_midpoint_sum),
                        -row,
                    ),
                )
                all_characters = [character for row in ordered_rows for character in characters_by_row[row]]
        else:
            raise InvalidCharacterSortError(sort)

        return all_characters

    def get_characters_grouped(
        self,
        grouping: CharacterGroup = CharacterGroup.ROW_TOP_TO_BOTTOM,
        *,
        input_chars: bool = True,
        inner_fill_chars: bool = False,
        outer_fill_chars: bool = False,
        added_chars: bool = False,
    ) -> list[list[EffectCharacter]]:
        """Get visible-canvas EffectCharacters grouped by the specified `CharacterGroup` grouping.

        Grouping uses each character's immutable input coordinate, not its current
        motion coordinate. Because the groups represent spatial regions of the canvas,
        selected added characters with input coordinates outside the canvas are omitted.
        Use `get_characters()` when a complete inventory, including off-canvas added
        characters, is required.

        Args:
            grouping (CharacterGroup, optional): order to group the characters. Defaults to ROW_TOP_TO_BOTTOM.
            input_chars (bool, optional): whether to include input characters. Defaults to True.
            inner_fill_chars (bool, optional): whether to include inner fill characters. Defaults to False.
            outer_fill_chars (bool, optional): whether to include outer fill characters. Defaults to False.
            added_chars (bool, optional): whether to include added characters. Defaults to False.

        Returns:
            list[list[EffectCharacter]]: List of lists of selected EffectCharacters within the visible canvas. Inner
                lists correspond to groups as specified in the grouping.

        Raises:
            InvalidCharacterGroupError: If an invalid grouping option is provided.

        """
        all_characters = self._get_selected_characters(
            input_chars=input_chars,
            inner_fill_chars=inner_fill_chars,
            outer_fill_chars=outer_fill_chars,
            added_chars=added_chars,
        )

        all_characters = [
            character
            for character in all_characters
            if (
                self.canvas.left <= character.input_coord.column <= self.canvas.right
                and self.canvas.bottom <= character.input_coord.row <= self.canvas.top
            )
        ]

        all_characters.sort(
            key=lambda character: (character.input_coord.row, character.input_coord.column),
        )

        if grouping in (
            CharacterGroup.COLUMN_LEFT_TO_RIGHT,
            CharacterGroup.COLUMN_RIGHT_TO_LEFT,
        ):
            characters_by_column: dict[int, list[EffectCharacter]] = {}
            for character in all_characters:
                column_index = character.input_coord.column
                characters_by_column.setdefault(column_index, []).append(character)
            ordered_columns = sorted(
                characters_by_column,
                reverse=grouping is CharacterGroup.COLUMN_RIGHT_TO_LEFT,
            )
            return [characters_by_column[column_index] for column_index in ordered_columns]

        if grouping in (
            CharacterGroup.ROW_BOTTOM_TO_TOP,
            CharacterGroup.ROW_TOP_TO_BOTTOM,
        ):
            characters_by_row: dict[int, list[EffectCharacter]] = {}
            for character in all_characters:
                row_index = character.input_coord.row
                characters_by_row.setdefault(row_index, []).append(character)
            ordered_rows = sorted(
                characters_by_row,
                reverse=grouping is CharacterGroup.ROW_TOP_TO_BOTTOM,
            )
            return [characters_by_row[row_index] for row_index in ordered_rows]
        if grouping in (
            CharacterGroup.DIAGONAL_BOTTOM_LEFT_TO_TOP_RIGHT,
            CharacterGroup.DIAGONAL_TOP_RIGHT_TO_BOTTOM_LEFT,
        ):
            characters_by_diagonal: dict[int, list[EffectCharacter]] = {}
            for character in all_characters:
                diagonal_index = character.input_coord.row + character.input_coord.column
                characters_by_diagonal.setdefault(diagonal_index, []).append(character)
            ordered_diagonals = sorted(
                characters_by_diagonal,
                reverse=grouping is CharacterGroup.DIAGONAL_TOP_RIGHT_TO_BOTTOM_LEFT,
            )
            return [characters_by_diagonal[diagonal_index] for diagonal_index in ordered_diagonals]
        if grouping in (
            CharacterGroup.DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT,
            CharacterGroup.DIAGONAL_BOTTOM_RIGHT_TO_TOP_LEFT,
        ):
            characters_by_diagonal = {}
            for character in all_characters:
                diagonal_index = character.input_coord.column - character.input_coord.row
                characters_by_diagonal.setdefault(diagonal_index, []).append(character)
            ordered_diagonals = sorted(
                characters_by_diagonal,
                reverse=grouping is CharacterGroup.DIAGONAL_BOTTOM_RIGHT_TO_TOP_LEFT,
            )
            return [characters_by_diagonal[diagonal_index] for diagonal_index in ordered_diagonals]
        if grouping in (
            CharacterGroup.CENTER_TO_OUTSIDE,
            CharacterGroup.OUTSIDE_TO_CENTER,
        ):
            distance_map: dict[int, list[EffectCharacter]] = {}
            for character in all_characters:
                distance = abs(character.input_coord.column - self.canvas.text_center.column) + abs(
                    character.input_coord.row - self.canvas.text_center.row,
                )
                if distance not in distance_map:
                    distance_map[distance] = []
                distance_map[distance].append(character)
            ordered_distances = sorted(
                distance_map.keys(),
                reverse=grouping is CharacterGroup.OUTSIDE_TO_CENTER,
            )
            return [distance_map[distance] for distance in ordered_distances]

        raise InvalidCharacterGroupError(grouping)

    def get_character_by_input_coord(self, coord: Coord) -> EffectCharacter | None:
        """Get an EffectCharacter by its input coordinates.

        Lookup includes input and fill characters but not characters added through
        `add_character()`. A coordinate occupied by the continuation cell of a wide
        input symbol returns the owning `EffectCharacter`. Looking up an otherwise
        empty canvas coordinate materializes only that coordinate's fill character.

        Args:
            coord (Coord): input coordinates of the character

        Returns:
            EffectCharacter | None: the character at the specified coordinates, or None if no character is found

        """
        return self._get_or_create_fill_character(coord)

    def set_character_visibility(self, character: EffectCharacter, is_visible: bool) -> None:  # noqa: FBT001
        """Set whether a character participates in terminal rendering.

        This updates both the character's internal visibility flag and the terminal's
        tracked set of currently visible characters.

        Args:
            character (EffectCharacter): Character whose visibility should be updated.
            is_visible (bool): Whether the character should be visible.

        Raises:
            InvalidCharacterError: If `character` is not owned by this terminal.
            InvalidCharacterVisibilityError: If `is_visible` is not a boolean.

        """
        if (
            not isinstance(character, EffectCharacter)
            or character._terminal_owner_token is not self._character_ownership_token
        ):
            raise InvalidCharacterError(character)
        if not isinstance(is_visible, bool):
            raise InvalidCharacterVisibilityError(is_visible)
        character._is_visible = is_visible
        if is_visible:
            if character not in self._visible_characters:
                self._visible_characters.add(character)
                insertion_index = bisect_left(
                    self._visible_characters_by_id,
                    character._character_id,
                    key=_CHARACTER_ID_KEY,
                )
                self._visible_characters_by_id.insert(insertion_index, character)
                self._visible_character_layer_counts[character.layer] = (
                    self._visible_character_layer_counts.get(character.layer, 0) + 1
                )
                self._visible_character_order_dirty = True
        elif character in self._visible_characters:
            self._visible_characters.remove(character)
            character_index = bisect_left(
                self._visible_characters_by_id,
                character._character_id,
                key=_CHARACTER_ID_KEY,
            )
            self._visible_characters_by_id.pop(character_index)
            layer_count = self._visible_character_layer_counts[character.layer] - 1
            if layer_count:
                self._visible_character_layer_counts[character.layer] = layer_count
            else:
                del self._visible_character_layer_counts[character.layer]
            self._visible_character_order_dirty = True

    def _notify_character_layer_changed(self, character: EffectCharacter, previous_layer: int) -> None:
        """Update visible-layer counts after an owned character's layer changes."""
        if character not in self._visible_characters:
            return
        previous_layer_count = self._visible_character_layer_counts[previous_layer] - 1
        if previous_layer_count:
            self._visible_character_layer_counts[previous_layer] = previous_layer_count
        else:
            del self._visible_character_layer_counts[previous_layer]
        self._visible_character_layer_counts[character.layer] = (
            self._visible_character_layer_counts.get(character.layer, 0) + 1
        )
        self._visible_character_order_dirty = True

    def _get_visible_characters_in_painter_order(self) -> list[EffectCharacter]:
        """Return visible characters ordered by layer and then character ID."""
        if len(self._visible_character_layer_counts) <= 1:
            return self._visible_characters_by_id
        if self._visible_character_order_dirty:
            self._visible_characters_by_layer = sorted(self._visible_characters_by_id, key=_LAYER_KEY)
            self._visible_character_order_dirty = False
        return self._visible_characters_by_layer

    def get_formatted_output_string(self) -> str:
        """Get the formatted output string based on the current terminal state.

        This method refreshes the internal terminal representation and returns it as a
        newline-delimited string ordered for terminal printing from top row to bottom row.

        Returns:
            str: The formatted output string.

        """
        self._update_terminal_state()
        return "\n".join(self.terminal_state[::-1])

    def _render_single_cell_characters(self, visible_characters: list[EffectCharacter]) -> list[str]:
        """Render single-cell characters through dense or sparse row buffers."""
        dense_threshold = max(
            1,
            min(
                (self.visible_top * self.visible_right) // 4,
                max(16, self.visible_top * 2),
            ),
        )
        if len(visible_characters) >= dense_threshold:
            dense_rows = [list(self._blank_row) for _ in range(self.visible_top)]
            for character in visible_characters:
                row = character.motion.current_coord.row + self.canvas_row_offset
                column = character.motion.current_coord.column + self.canvas_column_offset
                if self.visible_bottom <= row <= self.visible_top and self.visible_left <= column <= self.visible_right:
                    dense_rows[row - 1][column - 1] = character.animation.current_character_visual.formatted_symbol
            return ["".join(row) for row in dense_rows]

        rows: list[list[str] | None] = [None] * self.visible_top
        for character in visible_characters:
            row = character.motion.current_coord.row + self.canvas_row_offset
            column = character.motion.current_coord.column + self.canvas_column_offset
            if self.visible_bottom <= row <= self.visible_top and self.visible_left <= column <= self.visible_right:
                row_index = row - 1
                row_cells = rows[row_index]
                if row_cells is None:
                    row_cells = list(self._blank_row)
                    rows[row_index] = row_cells
                row_cells[column - 1] = character.animation.current_character_visual.formatted_symbol
        return [self._blank_row if row is None else "".join(row) for row in rows]

    def _render_width_aware_characters(self, visible_characters: list[EffectCharacter]) -> list[str]:
        """Render characters while resolving overlapping double-cell footprints."""
        rows: list[list[str] | None] = [None] * self.visible_top
        owners: list[list[EffectCharacter | None] | None] = [None] * self.visible_top
        footprints: dict[EffectCharacter, tuple[int, int, int]] = {}
        for character in visible_characters:
            row = character.motion.current_coord.row + self.canvas_row_offset
            column = character.motion.current_coord.column + self.canvas_column_offset
            visual = character.animation.current_character_visual
            right_column = column + visual.cell_width - 1
            if (
                self.visible_bottom <= row <= self.visible_top
                and self.visible_left <= column
                and right_column <= self.visible_right
            ):
                row_index = row - 1
                column_index = column - 1
                row_cells = rows[row_index]
                if row_cells is None:
                    row_cells = list(self._blank_row)
                    rows[row_index] = row_cells
                existing_row_owners = owners[row_index]
                row_owners: list[EffectCharacter | None]
                if existing_row_owners is None:
                    row_owners = [None] * self.visible_right
                    owners[row_index] = row_owners
                else:
                    row_owners = existing_row_owners
                overwritten_characters = {
                    owner
                    for owner in row_owners[column_index:right_column]
                    if owner is not None
                }
                for overwritten_character in overwritten_characters:
                    old_row, old_column, old_width = footprints.pop(overwritten_character)
                    old_row_owners = owners[old_row]
                    old_row_cells = rows[old_row]
                    if old_row_owners is None or old_row_cells is None:
                        msg = "Rendered wide-character footprint has no backing row."
                        raise RuntimeError(msg)
                    for old_column_index in range(old_column, old_column + old_width):
                        if old_row_owners[old_column_index] is overwritten_character:
                            old_row_owners[old_column_index] = None
                            old_row_cells[old_column_index] = " "
                row_cells[column_index] = visual.formatted_symbol
                row_owners[column_index] = character
                for continuation_column in range(column_index + 1, column_index + visual.cell_width):
                    row_cells[continuation_column] = ""
                    row_owners[continuation_column] = character
                footprints[character] = (row_index, column_index, visual.cell_width)
        return [self._blank_row if row is None else "".join(row) for row in rows]

    def _update_terminal_state(self) -> None:
        """Rebuild the internal representation of the visible terminal state.

        Visible characters are rendered using current motion coordinates adjusted by
        canvas offsets. Lower layers are painted first; characters on the same layer
        are painted in ascending character-ID order, so the highest ID wins a
        collision. Characters outside the visible bounds are skipped.
        """
        visible_characters = self._get_visible_characters_in_painter_order()
        if all(character.animation.current_character_visual.cell_width == 1 for character in visible_characters):
            self.terminal_state = self._render_single_cell_characters(visible_characters)
        else:
            self.terminal_state = self._render_width_aware_characters(visible_characters)

    def prep_canvas(self) -> None:
        """Prepare the terminal for the effect.

        Hide the cursor, position the canvas, and write blank canvas rows.

        If `config.reuse_canvas` is `True`, the cursor is first moved to the previously
        saved canvas position before the blank rows are written. This is intended to let
        the current effect reuse the prior canvas area rather than advancing output
        further down the terminal.

        Note: Use of `config.reuse_canvas` is less predictable if other canvas dimension
        options differ between the last run and the current run.

        Repeated calls during the same output lifecycle are no-ops. A second terminal
        cannot prepare output until the active terminal has restored the cursor because
        DEC save/restore position state is terminal-global and does not support nesting.

        Raises:
            TerminalOutputActiveError: If another terminal currently owns stdout cursor state.

        """
        if self._output_prepared:
            return
        active_terminal = (
            self._active_output_terminal() if self._active_output_terminal is not None else None
        )
        if active_terminal is not None:
            raise TerminalOutputActiveError
        self._output_prepared = True
        type(self)._active_output_terminal = weakref.ref(self)
        try:
            sys.stdout.write(ansitools.hide_cursor())
            if self.config.reuse_canvas:
                self.move_cursor_to_top()
            for _ in range(self.visible_top):
                sys.stdout.write((" " * self.visible_right) + "\n")
            sys.stdout.write(ansitools.dec_save_cursor_position())
        except BaseException:
            self._release_output_ownership()
            with suppress(Exception):
                if not self.config.no_restore_cursor:
                    sys.stdout.write(ansitools.show_cursor())
                sys.stdout.flush()
            raise

    def _release_output_ownership(self) -> None:
        """Mark output inactive and release this terminal's global cursor ownership."""
        self._output_prepared = False
        active_terminal = (
            self._active_output_terminal() if self._active_output_terminal is not None else None
        )
        if active_terminal is self:
            type(self)._active_output_terminal = None

    def restore_cursor(self, end_symbol: str = "\n") -> None:
        """Restore cursor visibility when enabled and write the configured end symbol.

        If the `--no-eol` option is enabled, no end symbol is printed. If the
        `--no-restore-cursor` option is enabled, cursor visibility is not restored.

        Args:
            end_symbol (str, optional): Symbol to print after the effect completes.
                Defaults to a newline.

        """
        if not self._output_prepared:
            return
        self._release_output_ownership()
        if self.config.no_eol:
            end_symbol = ""
        if not self.config.no_restore_cursor:
            sys.stdout.write(ansitools.show_cursor())
        sys.stdout.write(end_symbol)
        sys.stdout.flush()

    def print(self, output_string: str) -> None:
        """Print the provided output string at the top of the current canvas.

        The cursor is restored to the saved canvas position, moved to the top of the
        canvas, and the output string is written to stdout.

        Args:
            output_string (str): The string to print.

        Raises:
            TerminalOutputNotPreparedError: If `prep_canvas()` has not started an output lifecycle.

        """
        if not self._output_prepared:
            operation = "print"
            raise TerminalOutputNotPreparedError(operation)
        self.move_cursor_to_top()
        sys.stdout.write(output_string)
        sys.stdout.flush()

    def enforce_framerate(self) -> None:
        """Enforce the frame rate set in the terminal config.

        Frame rate is enforced by sleeping if the time since the last frame is shorter than the expected frame delay.
        If the configured frame rate is `0`, frame rate limiting is disabled and this method returns immediately.
        """
        if self._frame_rate == 0:
            return
        frame_delay = 1 / self._frame_rate
        if (time_since_last_print := time.monotonic() - self._last_time_printed) < frame_delay:
            time.sleep(frame_delay - time_since_last_print)
        self._last_time_printed = time.monotonic()

    def move_cursor_to_top(self) -> None:
        """Restore the saved canvas cursor position and move to the top of the canvas.

        The saved cursor position is restored, immediately saved again as the current
        canvas origin, and then the cursor is moved up by the visible canvas height.

        Raises:
            TerminalOutputNotPreparedError: If `prep_canvas()` has not started an output lifecycle.

        """
        if not self._output_prepared:
            operation = "move_cursor_to_top"
            raise TerminalOutputNotPreparedError(operation)
        sys.stdout.write(ansitools.dec_restore_cursor_position())
        sys.stdout.write(ansitools.dec_save_cursor_position())
        sys.stdout.write(ansitools.move_cursor_up(self.visible_top))
