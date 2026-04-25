"""A module for managing the terminal state and output.

Classes:
    TerminalConfig: Configuration for the terminal.
    Canvas: Represents the canvas in the terminal. Canvas bounds are derived from the input text dimensions,
        terminal dimensions, and relevant TerminalConfig options.
    Terminal: A class for managing the terminal state and output.
"""

from __future__ import annotations

import random
import re
import shutil
import sys
import time
import typing
from dataclasses import dataclass
from typing import Literal

from terminaltexteffects.engine.base_character import EffectCharacter
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.utils import ansitools, argutils
from terminaltexteffects.utils.argutils import CharacterGroup, CharacterSort, ColorSort
from terminaltexteffects.utils.exceptions import (
    InvalidCharacterGroupError,
    InvalidCharacterSortError,
    InvalidColorSortError,
    UnsupportedAnsiSequenceError,
)
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.graphics import Color


@dataclass
class TerminalConfig(BaseConfig):
    """Configuration for the terminal.

    Attributes:
        tab_width (int): Number of spaces to use for a tab character.
        xterm_colors (bool): Convert any colors specified in RGB hex to the closest XTerm-256 color.
        no_color (bool): Disable all colors in the effect.
        terminal_background_color (Color): Background color of the terminal used by effects that depend on it.
        existing_color_handling (Literal['always','dynamic','ignore']): Specify handling of existing ANSI color
            sequences in the input data. 'always' will always use the input colors, ignoring any effect specific
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
            "Specify handling of existing 8-bit and 24-bit ANSI color sequences in the input data. 3-bit and 4-bit "
            "sequences are not supported. 'always' will always use the input colors, ignoring any effect specific "
            "colors. 'dynamic' will leave it to the effect implementation to apply input colors. 'ignore' will "
            "ignore the colors in the input data. Default is 'ignore'."
        ),
    )  # pyright: ignore[reportAssignmentType]
    (
        "Literal['always','dynamic','ignore'] : Specify handling of existing ANSI color sequences in the input data. "
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


@dataclass
class Canvas:
    """Represent the canvas in the terminal.

    The canvas bounds are derived from the input text dimensions, terminal dimensions,
    and `TerminalConfig` options such as explicit canvas sizing, text wrapping, and
    ignoring terminal dimensions.

    This class provides methods for working with the canvas, such as checking if a coordinate is within the canvas,
    getting random coordinates within the canvas, and getting a random coordinate outside the canvas.

    This class also provides attributes for the dimensions of the canvas, the extents of the text within the canvas,
    and the center of the canvas.

    Args:
        top (int): top row of the canvas
        right (int): right column of the canvas
        bottom (int): bottom row of the canvas. Defaults to 1.
        left (int): left column of the canvas. Defaults to 1.

    Attributes:
        top (int): top row of the canvas
        right (int): right column of the canvas
        bottom (int): bottom row of the canvas
        left (int): left column of the canvas
        center_row (int): row of the center of the canvas
        center_column (int): column of the center of the canvas
        center (Coord): coordinate of the center of the canvas
        width (int): width of the canvas
        height (int): height of the canvas
        text_left (int): left column of the text within the canvas
        text_right (int): right column of the text within the canvas
        text_top (int): top row of the text within the canvas
        text_bottom (int): bottom row of the text within the canvas
        text_width (int): width of the text within the canvas
        text_height (int): height of the text within the canvas
        text_center_row (int): row of the center of the text within the canvas
        text_center_column (int): column of the center of the text within the canvas
        text_center (Coord): coordinate of the center of the text within the canvas

    Methods:
        coord_is_in_canvas:
            Checks whether a coordinate is within the canvas.
        coord_is_in_text:
            Checks whether a coordinate is within the text boundary of the canvas.
        random_column:
            Get a random column position within the canvas.
        random_row:
            Get a random row position within the canvas.
        random_coord:
            Get a random coordinate within or outside the canvas.

    """

    top: int
    """int: top row of the canvas"""
    right: int
    """int: right column of the canvas"""
    bottom: int = 1
    """int: bottom row of the canvas"""
    left: int = 1
    """int: left column of the canvas"""

    def __post_init__(self) -> None:
        """Initialize derived canvas geometry and default text-boundary values."""
        self.center_row = max(self.top // 2, self.bottom)
        """int: row of the center of the canvas"""
        if self.top % 2 and self.top > 1:
            self.center_row += 1
        self.center_column = max(self.right // 2, self.left)
        """int: column of the center of the canvas"""
        if self.right % 2 and self.right > 1:
            self.center_column += 1
        self.center = Coord(self.center_column, self.center_row)
        """Coord: coordinate of the center of the canvas"""
        self.width = self.right
        """int: width of the canvas"""
        self.height = self.top
        """int: height of the canvas"""
        self.text_left = 0
        """int: left column of the text within the canvas"""
        self.text_right = 0
        """int: right column of the text within the canvas"""
        self.text_top = 0
        """int: top row of the text within the canvas"""
        self.text_bottom = 0
        """int: bottom row of the text within the canvas"""
        self.text_width = 0
        """int: width of the text within the canvas"""
        self.text_height = 0
        """int: height of the text within the canvas"""
        self.text_center_row = 0
        """int: row of the center of the text within the canvas"""
        self.text_center_column = 0
        """int: column of the center of the text within the canvas"""
        self.text_center = Coord(self.text_center_column, self.text_center_row)
        """Coord: coordinate of the center of the text within the canvas"""

    def _anchor_text(
        self,
        characters: list[EffectCharacter],
        anchor: Literal["n", "ne", "e", "se", "s", "sw", "w", "nw", "c"],
    ) -> list[EffectCharacter]:
        """Anchors the text within the canvas based on the specified anchor point.

        The `characters` argument must be non-empty; this method expects at least one
        character when calculating anchored text bounds.

        Args:
            characters (list[EffectCharacter]): Non-empty list of characters to reposition within the canvas.
            anchor (Literal["n", "ne", "e", "se", "s", "sw", "w", "nw", "c"]): Anchor point for the text
                within the Canvas.

        Returns:
            list[EffectCharacter]: List of characters anchored within the canvas. Only returns characters with
                coordinates within the canvas after anchoring.

        """
        # translate coordinate based on anchor within the canvas
        input_width = max([character._input_coord.column for character in characters])
        input_height = max([character._input_coord.row for character in characters])

        column_delta = row_delta = 0
        if input_width != self.width:
            if anchor in ("s", "n", "c"):
                column_delta = self.center_column - (input_width // 2)
            elif anchor in ("se", "e", "ne"):
                column_delta = self.right - input_width
            elif anchor in ("sw", "w", "nw"):
                column_delta = self.left - 1
        if input_height != self.height:
            if anchor in ("w", "e", "c"):
                row_delta = self.center_row - (input_height // 2)
            elif anchor in ("nw", "n", "ne"):
                row_delta = self.top - input_height
            elif anchor in ("sw", "s", "se"):
                row_delta = self.bottom - 1

        for character in characters:
            current_coord = character.input_coord
            anchored_coord = Coord(
                current_coord.column + column_delta,
                current_coord.row + row_delta,
            )
            character._input_coord = anchored_coord
            character.motion.set_coordinate(anchored_coord)

        characters = [character for character in characters if self.coord_is_in_canvas(character.input_coord)]

        # get text dimensions, centers, and extents
        self.text_left = min([character.input_coord.column for character in characters])
        self.text_right = max([character.input_coord.column for character in characters])
        self.text_top = max([character.input_coord.row for character in characters])
        self.text_bottom = min([character.input_coord.row for character in characters])
        self.text_width = max(self.text_right - self.text_left + 1, 1)
        self.text_height = max(self.text_top - self.text_bottom + 1, 1)
        self.text_center_row = self.text_bottom + ((self.text_top - self.text_bottom) // 2)
        self.text_center_column = self.text_left + ((self.text_right - self.text_left) // 2)
        self.text_center = Coord(self.text_center_column, self.text_center_row)
        return characters

    def coord_is_in_canvas(self, coord: Coord) -> bool:
        """Check whether a coordinate is within the canvas.

        Args:
            coord (Coord): coordinate to check

        Returns:
            bool: whether the coordinate is within the canvas

        """
        return self.left <= coord.column <= self.right and self.bottom <= coord.row <= self.top

    def coord_is_in_text(self, coord: Coord) -> bool:
        """Check whether a coordinate is within the text boundary.

        Args:
            coord (Coord): coordinate to check

        Returns:
            bool: whether the coordinate is within the text boundary

        """
        return self.text_left <= coord.column <= self.text_right and self.text_bottom <= coord.row <= self.text_top

    def random_column(self, *, within_text_boundary: bool = False) -> int:
        """Get a random column position within the canvas.

        Args:
            within_text_boundary (bool, optional): If True, the column will be limited to the text boundary. Otherwise,
                it can be anywhere within the canvas. Defaults to False.

        Returns:
            int: a random column position within the canvas

        """
        if within_text_boundary:
            return random.randint(self.text_left, self.text_right)
        return random.randint(self.left, self.right)

    def random_row(self, *, within_text_boundary: bool = False) -> int:
        """Get a random row position within the canvas.

        Args:
            within_text_boundary (bool, optional): If True, the row will be limited to the text boundary. Otherwise,
                it can be anywhere within the canvas. Defaults to False.

        Returns:
            int: a random row position within the canvas

        """
        if within_text_boundary:
            return random.randint(self.text_bottom, self.text_top)
        return random.randint(self.bottom, self.top)

    def random_coord(
        self,
        *,
        outside_scope: bool = False,
        within_text_boundary: bool = False,
    ) -> Coord:
        """Get a random coordinate.

        The coordinate is within the canvas unless `outside_scope` is True. When
        `outside_scope` is True, the returned coordinate is positioned exactly one cell
        beyond one of the four canvas edges.

        `outside_scope` takes precedence over `within_text_boundary`; the two options are
        functionally mutually exclusive.

        Args:
            outside_scope (bool, optional): whether the coordinate should fall outside the canvas. Defaults to False.
            within_text_boundary (bool, optional): If True, the coordinate will be limited to the text boundary.
                Otherwise, it can be anywhere within the canvas. Defaults to False.

        Returns:
            Coord: A random coordinate. The coordinate is within the canvas unless `outside_scope` is `True`.

        """
        if outside_scope is True:
            random_coord_above = Coord(self.random_column(), self.top + 1)
            random_coord_below = Coord(self.random_column(), self.bottom - 1)
            random_coord_left = Coord(self.left - 1, self.random_row())
            random_coord_right = Coord(self.right + 1, self.random_row())
            return random.choice(
                [random_coord_above, random_coord_below, random_coord_left, random_coord_right],
            )
        return Coord(
            self.random_column(within_text_boundary=within_text_boundary),
            self.random_row(within_text_boundary=within_text_boundary),
        )


class Terminal:
    """A class for managing the terminal state and output.

    The terminal tracks input characters, fill characters, added characters, and the
    currently visible rendered state for the active canvas.

    Attributes:
        config (TerminalConfig): Configuration for the terminal.
        canvas (Canvas): The canvas in the terminal.
        character_by_input_coord (dict[Coord, EffectCharacter]): Mapping of input and fill characters keyed by
            canvas coordinates. Characters created with `add_character()` are tracked separately.
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
        set_character_visibility:
            Set the visibility of a character.
        get_formatted_output_string:
            Get the formatted output string based on the current terminal state.
        print:
            Prints the current terminal state to stdout while preserving the cursor position.

    """

    ansi_sequence_color_map: typing.ClassVar[dict[str, Color]] = {}
    ansi_escape_sequence_pattern: typing.ClassVar[re.Pattern[str]] = re.compile(
        r"(?:\x1b\][^\x07]*(?:\x07|\x1b\\))|(?:\x1b\[[0-?]*[ -/]*[@-~])|(?:\x1b.)",
    )
    csi_sequence_pattern: typing.ClassVar[re.Pattern[str]] = re.compile(r"\x1b\[([0-?]*)([ -/]*)([@-~])")

    def __init__(self, input_data: str, config: TerminalConfig | None = None) -> None:
        """Initialize the Terminal.

        Args:
            input_data (str): The input data to be displayed in the terminal.
            config (TerminalConfig, optional): Configuration for the terminal. Defaults to None.

        """
        if config is None:
            self.config = TerminalConfig._build_config()
        else:
            self.config = config
        if not input_data:
            input_data = "No Input."
        self._next_character_id = 0
        self._input_colors_frequency: dict[Color, int] = {}
        self._preprocessed_character_lines = self._preprocess_input_data(input_data)
        self._terminal_width, self._terminal_height = self._get_terminal_dimensions()
        self.canvas = Canvas(*self._get_canvas_dimensions())
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
        self._added_characters: list[EffectCharacter] = []
        self.character_by_input_coord: dict[Coord, EffectCharacter] = {
            (character.input_coord): character for character in self._input_characters
        }
        self._inner_fill_characters, self._outer_fill_characters = self._make_fill_characters()
        self._setup_character_neighbors()
        self._visible_characters: set[EffectCharacter] = set()
        self._frame_rate = self.config.frame_rate
        self._last_time_printed = time.monotonic()
        self._update_terminal_state()

    def _preprocess_input_data(self, input_data: str) -> list[list[EffectCharacter]]:  # noqa: PLR0915
        """Preprocess the input data.

        Input is decomposed into `EffectCharacter` rows while tracking supported
        SGR foreground/background color sequences and fetch-style cursor movement
        sequences. Unsupported ANSI/control sequences raise `UnsupportedAnsiSequenceError`.

        Args:
            input_data (str): The input data to be displayed in the terminal.

        Returns:
            list[list[EffectCharacter]]: Input characters decomposed into rows.

        """

        def build_color_sequence(color_code: int | str, sequence_type: str) -> str:
            """Build a normalized supported color SGR sequence."""
            if isinstance(color_code, int):
                return f"\x1b[{sequence_type};5;{color_code}m"
            color_ints = [int(color_code[index : index + 2], 16) for index in range(0, 6, 2)]
            return f"\x1b[{sequence_type};2;{color_ints[0]};{color_ints[1]};{color_ints[2]}m"

        def parse_csi_parameters(parameters: str) -> list[int]:
            """Parse CSI parameters, treating omitted values as zero."""
            if any(char not in "0123456789;" for char in parameters):
                msg = f"\x1b[{parameters}"
                raise UnsupportedAnsiSequenceError(msg)
            if not parameters:
                return []
            return [int(parameter) if parameter else 0 for parameter in parameters.split(";")]

        def apply_sgr_sequence(  # noqa: PLR0915
            sequence: str,
            active_sequences: dict[str, str],
            active_colors: dict[str, Color | None],
            active_styles: dict[str, bool],
            standard_fg_parameter: dict[str, int | None],
        ) -> None:
            """Apply supported SGR color parameters to the active input color state."""
            parameters = parse_csi_parameters(sequence[2:-1])
            if not parameters:
                parameters = [0]
            param_index = 0
            while param_index < len(parameters):
                parameter = parameters[param_index]
                if parameter == 0:  # SGR 0: reset all attributes
                    active_sequences["fg_color"] = active_sequences["bg_color"] = ""
                    active_colors["fg_color"] = active_colors["bg_color"] = None
                    active_styles["bold"] = False
                    standard_fg_parameter["fg_color"] = None
                elif parameter == 1:  # SGR 1: bold / increased intensity
                    active_styles["bold"] = True
                    if standard_fg_parameter["fg_color"] is not None:
                        active_colors["fg_color"] = Color(standard_fg_parameter["fg_color"] - 30 + 8)
                elif parameter == 22:  # SGR 22: normal intensity (not bold)
                    active_styles["bold"] = False
                    if standard_fg_parameter["fg_color"] is not None:
                        active_colors["fg_color"] = Color(standard_fg_parameter["fg_color"] - 30)
                elif parameter == 39:  # SGR 39: default foreground color
                    active_sequences["fg_color"] = ""
                    active_colors["fg_color"] = None
                    standard_fg_parameter["fg_color"] = None
                elif parameter == 49:  # SGR 49: default background color
                    active_sequences["bg_color"] = ""
                    active_colors["bg_color"] = None
                elif 30 <= parameter <= 37:  # SGR 30-37: standard foreground colors
                    color = Color(parameter - 30 + (8 if active_styles["bold"] else 0))
                    active_sequences["fg_color"] = f"\x1b[{parameter}m"
                    active_colors["fg_color"] = color
                    standard_fg_parameter["fg_color"] = parameter
                elif 90 <= parameter <= 97:  # SGR 90-97: bright foreground colors
                    color = Color(parameter - 90 + 8)
                    active_sequences["fg_color"] = f"\x1b[{parameter}m"
                    active_colors["fg_color"] = color
                    standard_fg_parameter["fg_color"] = None
                elif 40 <= parameter <= 47:  # SGR 40-47: standard background colors
                    color = Color(parameter - 40)
                    active_sequences["bg_color"] = f"\x1b[{parameter}m"
                    active_colors["bg_color"] = color
                elif 100 <= parameter <= 107:  # SGR 100-107: bright background colors
                    color = Color(parameter - 100 + 8)
                    active_sequences["bg_color"] = f"\x1b[{parameter}m"
                    active_colors["bg_color"] = color
                elif parameter in (38, 48):  # SGR 38/48: extended foreground/background color
                    if param_index + 1 >= len(parameters):
                        raise UnsupportedAnsiSequenceError(sequence)
                    sequence_type = "fg_color" if parameter == 38 else "bg_color"
                    color_sequence_type = str(parameter)
                    color_mode = parameters[param_index + 1]
                    if color_mode == 5:  # SGR ...;5;n: 8-bit indexed color
                        if param_index + 2 >= len(parameters):
                            raise UnsupportedAnsiSequenceError(sequence)
                        color_code: int | str = parameters[param_index + 2]
                        color = Color(color_code)
                        param_index += 2
                    elif color_mode == 2:  # SGR ...;2;r;g;b: 24-bit RGB color
                        if param_index + 4 >= len(parameters):
                            raise UnsupportedAnsiSequenceError(sequence)
                        color_code = "".join(f"{parameters[param_index + offset]:02X}" for offset in range(2, 5))
                        color = Color(color_code)
                        param_index += 4
                    else:
                        raise UnsupportedAnsiSequenceError(sequence)
                    active_sequences[sequence_type] = build_color_sequence(color_code, color_sequence_type)
                    active_colors[sequence_type] = color
                    if sequence_type == "fg_color":
                        standard_fg_parameter["fg_color"] = None
                param_index += 1

        def default_parameter(parameters: list[int]) -> int:
            """Return the first CSI parameter, defaulting zero/omitted values to one."""
            if not parameters:
                return 1
            return max(parameters[0], 1)

        def is_supported_private_mode_sequence(sequence: str) -> bool:
            """Return whether a CSI private mode sequence is safe to ignore while parsing input."""
            return sequence in {"\x1b[?25h", "\x1b[?25l", "\x1b[?7h", "\x1b[?7l"}

        def apply_cursor_sequence(sequence: str, row: int, column: int) -> tuple[int, int]:
            """Apply a supported cursor movement sequence and return the new cursor position."""
            csi_match = self.csi_sequence_pattern.fullmatch(sequence)
            if not csi_match:
                raise UnsupportedAnsiSequenceError(sequence)
            parameters_text, intermediates, final_byte = csi_match.groups()
            if intermediates:
                raise UnsupportedAnsiSequenceError(sequence)
            if parameters_text.startswith("?"):
                raise UnsupportedAnsiSequenceError(sequence)
            parameters = parse_csi_parameters(parameters_text)
            if final_byte == "A":  # CSI A: cursor up
                row -= default_parameter(parameters)
            elif final_byte == "B":  # CSI B: cursor down
                row += default_parameter(parameters)
            elif final_byte == "C":  # CSI C: cursor forward
                column += default_parameter(parameters)
            elif final_byte == "D":  # CSI D: cursor back
                column -= default_parameter(parameters)
            elif final_byte == "E":  # CSI E: cursor next line
                row += default_parameter(parameters)
                column = 0
            elif final_byte == "F":  # CSI F: cursor previous line
                row -= default_parameter(parameters)
                column = 0
            elif final_byte == "G":  # CSI G: cursor horizontal absolute
                column = default_parameter(parameters) - 1
            elif final_byte in ("H", "f"):  # CSI H/f: cursor position / horizontal-vertical position
                row = default_parameter(parameters) - 1
                column = (parameters[1] if len(parameters) > 1 and parameters[1] else 1) - 1
            else:
                raise UnsupportedAnsiSequenceError(sequence)
            return max(row, 0), max(column, 0)

        def build_character(
            symbol: str,
            active_sequences: dict[str, str],
            active_colors: dict[str, Color | None],
            active_styles: dict[str, bool],
        ) -> EffectCharacter:
            """Build an input character with the current terminal configuration and input colors."""
            character = EffectCharacter(self._next_character_id, symbol, 0, 0)
            self._next_character_id += 1
            for sequence_type, sequence in active_sequences.items():
                color = active_colors[sequence_type]
                if sequence and color:
                    character._input_ansi_sequences[sequence_type] = sequence
                    self._input_colors_frequency[color] = self._input_colors_frequency.get(color, 0) + 1
                    if sequence_type == "fg_color":
                        character.animation.input_fg_color = color
                    else:
                        character.animation.input_bg_color = color
            character.animation.input_bold = active_styles["bold"]
            character.animation.no_color = self.config.no_color
            character.animation.use_xterm_colors = self.config.xterm_colors
            character.animation.existing_color_handling = self.config.existing_color_handling
            character.uses_input_preexisting_colors = True
            if character.animation.existing_color_handling == "always":
                character.animation.set_appearance(character.input_symbol)
            return character

        screen: dict[tuple[int, int], EffectCharacter] = {}
        active_sequences = {"fg_color": "", "bg_color": ""}
        active_colors: dict[str, Color | None] = {"fg_color": None, "bg_color": None}
        active_styles = {"bold": False}
        standard_fg_parameter: dict[str, int | None] = {"fg_color": None}
        row = column = 0
        char_index = max_row = max_column = 0
        while char_index < len(input_data):
            if input_data[char_index] == "\x1b":
                sequence_match = self.ansi_escape_sequence_pattern.match(input_data, char_index)
                if not sequence_match:
                    raise UnsupportedAnsiSequenceError(input_data[char_index])
                sequence = sequence_match.group(0)
                if sequence.startswith("\x1b["):
                    csi_match = self.csi_sequence_pattern.fullmatch(sequence)
                    if not csi_match:
                        raise UnsupportedAnsiSequenceError(sequence)
                    final_byte = csi_match.group(3)
                    if final_byte == "m":
                        apply_sgr_sequence(
                            sequence,
                            active_sequences,
                            active_colors,
                            active_styles,
                            standard_fg_parameter,
                        )
                    elif is_supported_private_mode_sequence(sequence):
                        pass
                    else:
                        row, column = apply_cursor_sequence(sequence, row, column)
                        max_row = max(max_row, row)
                        max_column = max(max_column, column)
                else:
                    raise UnsupportedAnsiSequenceError(sequence)
                char_index = sequence_match.end()
            elif input_data[char_index] == "\n":
                row += 1
                column = 0
                max_row = max(max_row, row)
                char_index += 1
            elif input_data[char_index] == "\r":
                column = 0
                char_index += 1
            else:
                symbol = input_data[char_index]
                if symbol == "\t":
                    symbol = " "
                    spaces_to_next_tab = self.config.tab_width - (column % self.config.tab_width)
                else:
                    spaces_to_next_tab = 1
                for _ in range(spaces_to_next_tab):
                    screen[(row, column)] = build_character(symbol, active_sequences, active_colors, active_styles)
                    max_row = max(max_row, row)
                    max_column = max(max_column, column)
                    column += 1
                char_index += 1

        characters: list[list[EffectCharacter]] = []
        for screen_row in range(max_row + 1):
            character_line: list[EffectCharacter] = []
            for screen_column in range(max_column + 1):
                character = screen.get((screen_row, screen_column))
                if character is None:
                    character = build_character(
                        " ",
                        {"fg_color": "", "bg_color": ""},
                        {"fg_color": None, "bg_color": None},
                        {"bold": False},
                    )
                character_line.append(character)
            while character_line and character_line[-1].input_symbol == " " and not any(
                (character_line[-1].animation.input_fg_color, character_line[-1].animation.input_bg_color),
            ):
                character_line.pop()
            characters.append(character_line)
        while characters and not characters[-1]:
            characters.pop()

        return characters or [[build_character(" ", active_sequences, active_colors, active_styles)]]

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
            canvas_column_offset = (self._terminal_width // 2) - (self.canvas.width // 2)
        elif self.config.anchor_canvas in ("se", "e", "ne"):
            canvas_column_offset = self._terminal_width - self.canvas.width
        if self.config.anchor_canvas in ("w", "e", "c"):
            canvas_row_offset = self._terminal_height // 2 - self.canvas.height // 2
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
            input_width = max([len(line) for line in self._preprocessed_character_lines])
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
            if self.config.ignore_terminal_dimensions:
                canvas_height = input_height
            elif self.config.wrap_text:
                canvas_height = min(
                    len(self._wrap_lines(self._preprocessed_character_lines, canvas_width)),
                    self._terminal_height,
                )
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
        for line in lines:
            current_line = line
            while len(current_line) > width:
                wrapped_lines.append(current_line[:width])
                current_line = current_line[width:]
            wrapped_lines.append(current_line)
        return wrapped_lines

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
        formatted_lines = []
        formatted_lines = (
            self._wrap_lines(self._preprocessed_character_lines, self.canvas.right)
            if self.config.wrap_text
            else self._preprocessed_character_lines
        )
        input_height = len(formatted_lines)
        input_characters: list[EffectCharacter] = []
        for row, line in enumerate(formatted_lines):
            for column, character in enumerate(line, start=1):
                character._input_coord = Coord(column, input_height - row)
                if character._input_symbol != " " or any(
                    (character.animation.input_fg_color, character.animation.input_bg_color),
                ):
                    input_characters.append(character)

        anchored_characters = self.canvas._anchor_text(input_characters, self.config.anchor_text)
        return [char for char in anchored_characters if self.canvas.coord_is_in_canvas(char._input_coord)]

    def _make_fill_characters(self) -> tuple[list[EffectCharacter], list[EffectCharacter]]:
        """Create fill characters for unoccupied canvas coordinates.

        Fill characters use a space as `input_symbol` and are inserted into
        `character_by_input_coord` for any canvas coordinate not already occupied by an
        input character. They are split into inner and outer fill characters based on
        whether the coordinate falls within the anchored text bounds.

        Returns:
            tuple[list[EffectCharacter], list[EffectCharacter]]: Lists of inner and outer
                fill characters.

        """
        inner_fill_characters = []
        outer_fill_characters = []
        for row in range(1, self.canvas.top + 1):
            for column in range(1, self.canvas.right + 1):
                coord = Coord(column, row)
                if coord not in self.character_by_input_coord:
                    fill_char = EffectCharacter(self._next_character_id, " ", column, row)
                    fill_char.is_fill_character = True
                    fill_char.animation.no_color = self.config.no_color
                    fill_char.animation.use_xterm_colors = self.config.xterm_colors
                    fill_char.animation.existing_color_handling = self.config.existing_color_handling
                    fill_char.uses_input_preexisting_colors = False
                    self.character_by_input_coord[coord] = fill_char
                    self._next_character_id += 1
                    if (
                        self.canvas.text_left <= column <= self.canvas.text_right
                        and self.canvas.text_bottom <= row <= self.canvas.text_top
                    ):
                        inner_fill_characters.append(fill_char)
                    else:
                        outer_fill_characters.append(fill_char)
        return inner_fill_characters, outer_fill_characters

    def _setup_character_neighbors(self) -> None:
        """Create the neighbor map for characters tracked in `character_by_input_coord`."""
        delta_map = {"north": (0, 1), "east": (1, 0), "south": (0, -1), "west": (-1, 0)}
        for coord, char in self.character_by_input_coord.items():
            for direction, delta in delta_map.items():
                neighbor_coord = Coord(column=coord.column + delta[0], row=coord.row + delta[1])
                char.neighbors[direction] = self.character_by_input_coord.get(neighbor_coord)

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

        """
        character = EffectCharacter(self._next_character_id, symbol, coord.column, coord.row)
        character.animation.no_color = self.config.no_color
        character.animation.use_xterm_colors = self.config.xterm_colors
        character.animation.existing_color_handling = self.config.existing_color_handling
        character.uses_input_preexisting_colors = False

        self._added_characters.append(character)
        self._next_character_id += 1
        return character

    def get_input_colors(self, sort: ColorSort = ColorSort.MOST_TO_LEAST) -> list[Color]:
        """Get colors derived from supported input color sequences with an optional sort.

        Args:
            sort (ColorSort, optional): Sort order for the colors.
                Defaults to `ColorSort.MOST_TO_LEAST`.

        Raises:
            InvalidColorSortError: If an invalid sort option is provided.

        Returns:
            list[Color]: Input colors tracked during preprocessing.

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

    def get_characters(
        self,
        *,
        input_chars: bool = True,
        inner_fill_chars: bool = False,
        outer_fill_chars: bool = False,
        added_chars: bool = False,
        sort: CharacterSort = CharacterSort.TOP_TO_BOTTOM_LEFT_TO_RIGHT,
    ) -> list[EffectCharacter]:
        """Get a list of all EffectCharacters in the terminal with an optional sort.

        Sorting is based on character input coordinates. The row-based "outside/middle"
        sort options interleave characters from the beginning and end of the default
        top-to-bottom, left-to-right ordering.

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
        all_characters: list[EffectCharacter] = []
        if input_chars:
            all_characters.extend(self._input_characters)
        if inner_fill_chars:
            all_characters.extend(self._inner_fill_characters)
        if outer_fill_chars:
            all_characters.extend(self._outer_fill_characters)
        if added_chars:
            all_characters.extend(self._added_characters)

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
            all_characters = [
                all_characters.pop(0) if i % 2 == 0 else all_characters.pop(-1) for i in range(len(all_characters))
            ]
            if sort is CharacterSort.MIDDLE_ROW_TO_OUTSIDE:
                all_characters.reverse()
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
        """Get a list of all EffectCharacters grouped by the specified CharacterGroup grouping.

        Args:
            grouping (CharacterGroup, optional): order to group the characters. Defaults to ROW_TOP_TO_BOTTOM.
            input_chars (bool, optional): whether to include input characters. Defaults to True.
            inner_fill_chars (bool, optional): whether to include inner fill characters. Defaults to False.
            outer_fill_chars (bool, optional): whether to include outer fill characters. Defaults to False.
            added_chars (bool, optional): whether to include added characters. Defaults to False.

        Returns:
            list[list[EffectCharacter]]: list of lists of EffectCharacters in the terminal. Inner lists correspond
                to groups as specified in the grouping.

        Raises:
            InvalidCharacterGroupError: If an invalid grouping option is provided.

        """
        all_characters: list[EffectCharacter] = []
        if input_chars:
            all_characters.extend(self._input_characters)
        if inner_fill_chars:
            all_characters.extend(self._inner_fill_characters)
        if outer_fill_chars:
            all_characters.extend(self._outer_fill_characters)
        if added_chars:
            all_characters.extend(self._added_characters)

        all_characters.sort(
            key=lambda character: (character.input_coord.row, character.input_coord.column),
        )

        if grouping in (
            CharacterGroup.COLUMN_LEFT_TO_RIGHT,
            CharacterGroup.COLUMN_RIGHT_TO_LEFT,
        ):
            columns = []
            for column_index in range(self.canvas.right + 1):
                characters_in_column = [
                    character for character in all_characters if character.input_coord.column == column_index
                ]
                if characters_in_column:
                    columns.append(characters_in_column)
            if grouping == CharacterGroup.COLUMN_RIGHT_TO_LEFT:
                columns.reverse()
            return columns

        if grouping in (
            CharacterGroup.ROW_BOTTOM_TO_TOP,
            CharacterGroup.ROW_TOP_TO_BOTTOM,
        ):
            rows = []
            for row_index in range(self.canvas.top + 1):
                characters_in_row = [
                    character for character in all_characters if character.input_coord.row == row_index
                ]
                if characters_in_row:
                    rows.append(characters_in_row)
            if grouping == CharacterGroup.ROW_TOP_TO_BOTTOM:
                rows.reverse()
            return rows
        if grouping in (
            CharacterGroup.DIAGONAL_BOTTOM_LEFT_TO_TOP_RIGHT,
            CharacterGroup.DIAGONAL_TOP_RIGHT_TO_BOTTOM_LEFT,
        ):
            diagonals = []
            for diagonal_index in range(self.canvas.top + self.canvas.right + 1):
                characters_in_diagonal = [
                    character
                    for character in all_characters
                    if character.input_coord.row + character.input_coord.column == diagonal_index
                ]
                if characters_in_diagonal:
                    diagonals.append(characters_in_diagonal)
            if grouping == CharacterGroup.DIAGONAL_TOP_RIGHT_TO_BOTTOM_LEFT:
                diagonals.reverse()
            return diagonals
        if grouping in (
            CharacterGroup.DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT,
            CharacterGroup.DIAGONAL_BOTTOM_RIGHT_TO_TOP_LEFT,
        ):
            diagonals = []
            for diagonal_index in range(
                self.canvas.left - self.canvas.top,
                self.canvas.right - self.canvas.bottom + 1,
            ):
                characters_in_diagonal = [
                    character
                    for character in all_characters
                    if character.input_coord.column - character.input_coord.row == diagonal_index
                ]
                if characters_in_diagonal:
                    diagonals.append(characters_in_diagonal)
            if grouping == CharacterGroup.DIAGONAL_BOTTOM_RIGHT_TO_TOP_LEFT:
                diagonals.reverse()
            return diagonals
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

        Lookup is limited to characters stored in `character_by_input_coord`, which
        includes input and fill characters but not characters added through
        `add_character()`.

        Args:
            coord (Coord): input coordinates of the character

        Returns:
            EffectCharacter | None: the character at the specified coordinates, or None if no character is found

        """
        return self.character_by_input_coord.get(coord, None)

    def set_character_visibility(self, character: EffectCharacter, is_visible: bool) -> None:  # noqa: FBT001
        """Set whether a character participates in terminal rendering.

        This updates both the character's internal visibility flag and the terminal's
        tracked set of currently visible characters.

        Args:
            character (EffectCharacter): Character whose visibility should be updated.
            is_visible (bool): Whether the character should be visible.

        """
        character._is_visible = is_visible
        if is_visible:
            self._visible_characters.add(character)
        else:
            self._visible_characters.discard(character)

    def get_formatted_output_string(self) -> str:
        """Get the formatted output string based on the current terminal state.

        This method refreshes the internal terminal representation and returns it as a
        newline-delimited string ordered for terminal printing from top row to bottom row.

        Returns:
            str: The formatted output string.

        """
        self._update_terminal_state()
        return "\n".join(self.terminal_state[::-1])

    def _update_terminal_state(self) -> None:
        """Rebuild the internal representation of the visible terminal state.

        A blank buffer covering the visible terminal area is created, then visible
        characters are rendered into it in ascending layer order using their current
        motion coordinates adjusted by the canvas offsets. Characters outside the visible
        bounds are skipped.
        """
        rows = [[" " for _ in range(self.visible_right)] for _ in range(self.visible_top)]
        for character in sorted(self._visible_characters, key=lambda c: c.layer):
            row = character.motion.current_coord.row + self.canvas_row_offset
            column = character.motion.current_coord.column + self.canvas_column_offset
            if self.visible_bottom <= row <= self.visible_top and self.visible_left <= column <= self.visible_right:
                rows[row - 1][column - 1] = character.animation.current_character_visual.formatted_symbol
        terminal_state = ["".join(row) for row in rows]
        self.terminal_state = terminal_state

    def prep_canvas(self) -> None:
        """Prepare the terminal for the effect.

        Hide the cursor, position the canvas, and write blank canvas rows.

        If `config.reuse_canvas` is `True`, the cursor is first moved to the previously
        saved canvas position before the blank rows are written. This is intended to let
        the current effect reuse the prior canvas area rather than advancing output
        further down the terminal.

        Note: Use of `config.reuse_canvas` is less predictable if other canvas dimension
        options differ between the last run and the current run.
        """
        sys.stdout.write(ansitools.hide_cursor())
        if self.config.reuse_canvas:
            self.move_cursor_to_top()
        for _ in range(self.visible_top):
            sys.stdout.write((" " * self.visible_right) + "\n")
        sys.stdout.write(ansitools.dec_save_cursor_position())

    def restore_cursor(self, end_symbol: str = "\n") -> None:
        """Restore cursor visibility when enabled and write the configured end symbol.

        If the `--no-eol` option is enabled, no end symbol is printed. If the
        `--no-restore-cursor` option is enabled, cursor visibility is not restored.

        Args:
            end_symbol (str, optional): Symbol to print after the effect completes.
                Defaults to a newline.

        """
        if self.config.no_eol:
            end_symbol = ""
        if not self.config.no_restore_cursor:
            sys.stdout.write(ansitools.show_cursor())
        sys.stdout.write(end_symbol)

    def print(self, output_string: str) -> None:
        """Print the provided output string at the top of the current canvas.

        The cursor is restored to the saved canvas position, moved to the top of the
        canvas, and the output string is written to stdout.

        Args:
            output_string (str): The string to print.

        """
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
        """
        sys.stdout.write(ansitools.dec_restore_cursor_position())
        sys.stdout.write(ansitools.dec_save_cursor_position())
        sys.stdout.write(ansitools.move_cursor_up(self.visible_top))
