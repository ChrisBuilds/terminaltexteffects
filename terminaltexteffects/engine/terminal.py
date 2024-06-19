"""A module for managing the terminal state and output.

Classes:
    TerminalConfig: Configuration for the terminal.
    Canvas: Represents the canvas in the terminal. The canvas is the area defined by the dimensions of the input data, unless specified otherwise in the TerminalConfig.
    Terminal: A class for managing the terminal state and output.
"""

from __future__ import annotations

import random
import shutil
import sys
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Literal

import terminaltexteffects.utils.argvalidators as argvalidators
from terminaltexteffects.engine.base_character import EffectCharacter
from terminaltexteffects.utils import ansitools
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass
from terminaltexteffects.utils.geometry import Coord


@dataclass
class TerminalConfig(ArgsDataClass):
    """Configuration for the terminal.

    Attributes:
        tab_width (int): Number of spaces to use for a tab character.
        xterm_colors (bool): Convert any colors specified in RBG hex to the closest XTerm-256 color.
        no_color (bool): Disable all colors in the effect.
        wrap_text (bool): Wrap text wider than the canvas width.
        frame_rate (float): Target frame rate for the animation.
        canvas_width (int): Cavas width, if set to 0 the canvas width is detected automatically based on the terminal device.
        canvas_height (int): Canvas height, if set to 0 the canvas height is detected automatically based on the terminal device.
        anchor_canvas (Literal['sw','s','se','e','ne','n','nw','w','c']): Anchor point for the Canvas. The Canvas will be anchored in the terminal to the location corresponding to the cardinal/diagonal direction. Defaults to 'sw'.
        anchor_effect (Literal['sw','s','se','e','ne','n','nw','w','c']): Anchor point for the effect within the Canvas. Effect text will anchored in the Canvas to the location corresponding to the cardinal/diagonal direction. Defaults to 'sw'.
        ignore_terminal_dimensions (bool): Ignore the terminal dimensions and utilize the full Canvas beyond the extents of the terminal. Useful for sending frames to another output handler.
    """

    tab_width: int = ArgField(
        cmd_name=["--tab-width"],
        type_parser=argvalidators.PositiveInt.type_parser,
        metavar=argvalidators.PositiveInt.METAVAR,
        default=4,
        help="Number of spaces to use for a tab character.",
    )  # type: ignore[assignment]

    "int : Number of spaces to use for a tab character."

    xterm_colors: bool = ArgField(
        cmd_name=["--xterm-colors"],
        default=False,
        action="store_true",
        help="Convert any colors specified in RBG hex to the closest XTerm-256 color.",
    )  # type: ignore[assignment]

    "bool : Convert any colors specified in RBG hex to the closest XTerm-256 color."

    no_color: bool = ArgField(
        cmd_name=["--no-color"], default=False, action="store_true", help="Disable all colors in the effect."
    )  # type: ignore[assignment]

    "bool : Disable all colors in the effect."

    wrap_text: int = ArgField(
        cmd_name="--wrap-text", default=False, action="store_true", help="Wrap text wider than the canvas width."
    )  # type: ignore[assignment]
    "bool : Wrap text wider than the canvas width."

    frame_rate: float = ArgField(
        cmd_name="--frame-rate",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=100,
        help="""Target frame rate for the animation.""",
    )  # type: ignore[assignment]

    "float : Minimum time, in seconds, between frames."

    canvas_width: int = ArgField(
        cmd_name=["--canvas-width"],
        metavar=argvalidators.CanvasDimension.METAVAR,
        type_parser=argvalidators.CanvasDimension.type_parser,
        default=-1,
        help="Canvas width, set to an integer > 0 to use a specific dimension, or use 0, or -1 to set the dimension based off the input data or the terminal device, respectively.",
    )  # type: ignore[assignment]

    "int : Canvas width, if set to 0 the canvas width is detected automatically based on the terminal device, if set to -1 the canvas width is based on the input data width."

    canvas_height: int = ArgField(
        cmd_name=["--canvas-height"],
        metavar=argvalidators.CanvasDimension.METAVAR,
        type_parser=argvalidators.CanvasDimension.type_parser,
        default=-1,
        help="Canvas height, set to an integer > 0 to use a specific dimension, or use 0, or -1 to set the dimension based off the input data or the terminal device, respectively.",
    )  # type: ignore[assignment]

    "int : Canvas height, if set to 0 the canvas height is is detected automatically based on the terminal device, if set to -1 the canvas width is based on the input data height."

    anchor_canvas: Literal["sw", "s", "se", "e", "ne", "n", "nw", "w", "c"] = ArgField(
        cmd_name=["--anchor-canvas"],
        choices=["sw", "s", "se", "e", "ne", "n", "nw", "w", "c"],
        default="sw",
        help="Anchor point for the canvas. The canvas will be anchored in the terminal to the location corresponding to the cardinal/diagonal direction.",
    )  # type: ignore[assignment]

    "Literal['sw','s','se','e','ne','n','nw','w','c'] : Anchor point for the canvas. The canvas will be anchored in the terminal to the location corresponding to the cardinal/diagonal direction."

    anchor_text: Literal["n", "ne", "e", "se", "s", "sw", "w", "nw", "c"] = ArgField(
        cmd_name=["--anchor-text"],
        choices=["n", "ne", "e", "se", "s", "sw", "w", "nw", "c"],
        default="sw",
        help="Anchor point for the text within the Canvas. Input text will anchored in the Canvas to the location corresponding to the cardinal/diagonal direction.",
    )  # type: ignore[assignment]

    "Literal['n','ne','e','se','s','sw','w','nw','c'] : Anchor point for the text within the Canvas. Input text will anchored in the Canvas to the location corresponding to the cardinal/diagonal direction."

    ignore_terminal_dimensions: bool = ArgField(
        cmd_name=["--ignore-terminal-dimensions"],
        default=False,
        action="store_true",
        help="Ignore the terminal dimensions and utilize the full Canvas beyond the extents of the terminal. Useful for sending frames to another output handler.",
    )  # type: ignore[assignment]
    "bool : Ignore the terminal dimensions and utilize the full Canvas beyond the extents of the terminal. Useful for sending frames to another output handler."


@dataclass
class Canvas:
    """Represents the canvas in the terminal. The canvas is the area defined
    by the dimensions of the input data, unless specified otherwise in the TerminalConfig.

    This class provides methods for working with the canvas, such as checking if a coordinate is within the canvas,
    getting random coordinates within the canvas, and getting a random coordinate outside the canvas.

    This class also provides attributes for the dimensions of the canvas, the extents of the text within the canvas, and the center of the canvas.

    Args:
        top (int): top row of the canvas
        right (int): right column of the canvas

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

    Methods:
        coord_is_in_canvas(coord: Coord) -> bool: Checks whether a coordinate is within the canvas.
        random_column() -> int: Get a random column position within the canvas.
        random_row() -> int: Get a random row position within the canvas.
        random_coord(outside_scope=False) -> Coord: Get a random coordinate within or outside the canvas.

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
        self.center_row = max(self.top // 2, self.bottom)
        """int: row of the center of the canvas"""
        self.center_column = max(self.right // 2, self.left)
        """int: column of the center of the canvas"""
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

    def _anchor_text(
        self, characters: list[EffectCharacter], anchor: Literal["n", "ne", "e", "se", "s", "sw", "w", "nw", "c"]
    ) -> list[EffectCharacter]:
        """Anchors the text within the canvas based on the specified anchor point.

        Args:
            characters (list[EffectCharacter]): _description_
            anchor (Literal["n", "ne", "e", "se", "s", "sw", "w", "nw", "c"]): Anchor point for the text within the Canvas.

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
            anchored_coord = Coord(current_coord.column + column_delta, current_coord.row + row_delta)
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

        return characters

    def coord_is_in_canvas(self, coord: Coord) -> bool:
        """Checks whether a coordinate is within the canvas.

        Args:
            coord (Coord): coordinate to check

        Returns:
            bool: whether the coordinate is within the canvas
        """
        return self.left <= coord.column <= self.right and self.bottom <= coord.row <= self.top

    def random_column(self) -> int:
        """Get a random column position. Position is within the canvas.

        Returns:
            int: a random column position (1 <= x <= canvas.right)"""
        return random.randint(self.left, self.right)

    def random_row(self) -> int:
        """Get a random row position. Position is within the canvas.

        Returns:
            int: a random row position (1 <= x <= terminal.canvas.top)"""
        return random.randint(self.bottom, self.top)

    def random_coord(self, outside_scope=False) -> Coord:
        """Get a random coordinate. Coordinate is within the canvas unless outside_scope is True.

        Args:
            outside_scope (bool, optional): whether the coordinate should fall outside the canvas. Defaults to False.

        Returns:
            Coord: a random coordinate . Coordinate is within the canvas unless outside_scope is True."""
        if outside_scope is True:
            random_coord_above = Coord(self.random_column(), self.top + 1)
            random_coord_below = Coord(self.random_column(), self.bottom - 1)
            random_coord_left = Coord(self.left - 1, self.random_row())
            random_coord_right = Coord(self.right + 1, self.random_row())
            return random.choice([random_coord_above, random_coord_below, random_coord_left, random_coord_right])
        else:
            return Coord(self.random_column(), self.random_row())


class Terminal:
    """A class for managing the terminal state and output.

    Attributes:
        config (TerminalConfig): Configuration for the terminal.
        canvas (Canvas): The canvas in the terminal.
        character_by_input_coord (dict[Coord, EffectCharacter]): A dictionary of characters by their input coordinates.

    Methods:
        get_piped_input() -> str: Gets the piped input from stdin.
        prep_canvas(): Prepares the terminal for the effect by adding empty lines and hiding the cursor.
        restore_cursor(): Restores the cursor visibility.
        get_characters(input_characters: bool = True, fill_chars: bool = False, added_chars: bool = False, sort: CharacterSort = CharacterSort.TOP_TO_BOTTOM_LEFT_TO_RIGHT) -> list[EffectCharacter]: Get a list of all EffectCharacters in the terminal with an optional sort.
        get_characters_grouped(grouping: CharacterGroup = CharacterGroup.ROW_TOP_TO_BOTTOM, input_characters: bool = True, fill_chars: bool = False, added_chars: bool = False) -> list[list[EffectCharacter]]: Get a list of all EffectCharacters grouped by the specified CharacterGroup grouping.
        get_character_by_input_coord(coord: Coord) -> EffectCharacter | None: Get an EffectCharacter by its input coordinates.
        set_character_visibility(character: EffectCharacter, is_visible: bool): Set the visibility of a character.
        get_formatted_output_string() -> str: Get the formatted output string based on the current terminal state.
        print(output_string: str, enforce_frame_rate: bool = True): Prints the current terminal state to stdout while preserving the cursor position.

    """

    class CharacterGroup(Enum):
        """An enum specifying character groupings.

        Attributes:
            COLUMN_LEFT_TO_RIGHT: Group characters by column from left to right.
            COLUMN_RIGHT_TO_LEFT: Group characters by column from right to left.
            ROW_TOP_TO_BOTTOM: Group characters by row from top to bottom.
            ROW_BOTTOM_TO_TOP: Group characters by row from bottom to top.
            DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT: Group characters by diagonal from top left to bottom right.
            DIAGONAL_BOTTOM_LEFT_TO_TOP_RIGHT: Group characters by diagonal from bottom left to top right.
            DIAGONAL_TOP_RIGHT_TO_BOTTOM_LEFT: Group characters by diagonal from top right to bottom left.
            DIAGONAL_BOTTOM_RIGHT_TO_TOP_LEFT: Group characters by diagonal from bottom right to top left.
            CENTER_TO_OUTSIDE_DIAMONDS: Group characters by distance from the center to the outside in diamond shapes.
            OUTSIDE_TO_CENTER_DIAMONDS: Group characters by distance from the outside to the center in diamond shapes.
        """

        COLUMN_LEFT_TO_RIGHT = auto()
        COLUMN_RIGHT_TO_LEFT = auto()
        ROW_TOP_TO_BOTTOM = auto()
        ROW_BOTTOM_TO_TOP = auto()
        DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT = auto()
        DIAGONAL_BOTTOM_LEFT_TO_TOP_RIGHT = auto()
        DIAGONAL_TOP_RIGHT_TO_BOTTOM_LEFT = auto()
        DIAGONAL_BOTTOM_RIGHT_TO_TOP_LEFT = auto()
        CENTER_TO_OUTSIDE_DIAMONDS = auto()
        OUTSIDE_TO_CENTER_DIAMONDS = auto()

    class CharacterSort(Enum):
        """An enum for specifying character sorts.

        Attributes:
            RANDOM: Random order.
            TOP_TO_BOTTOM_LEFT_TO_RIGHT: Top to bottom, left to right.
            TOP_TO_BOTTOM_RIGHT_TO_LEFT: Top to bottom, right to left.
            BOTTOM_TO_TOP_LEFT_TO_RIGHT: Bottom to top, left to right.
            BOTTOM_TO_TOP_RIGHT_TO_LEFT: Bottom to top, right to left.
            OUTSIDE_ROW_TO_MIDDLE: Outside row to middle.
            MIDDLE_ROW_TO_OUTSIDE: Middle row to outside.
        """

        RANDOM = auto()
        TOP_TO_BOTTOM_LEFT_TO_RIGHT = auto()
        TOP_TO_BOTTOM_RIGHT_TO_LEFT = auto()
        BOTTOM_TO_TOP_LEFT_TO_RIGHT = auto()
        BOTTOM_TO_TOP_RIGHT_TO_LEFT = auto()
        OUTSIDE_ROW_TO_MIDDLE = auto()
        MIDDLE_ROW_TO_OUTSIDE = auto()

    def __init__(self, input_data: str, config: TerminalConfig | None = None):
        """Initializes the Terminal object.

        Args:
            input_data (str): The input data to be displayed in the terminal.
            config (TerminalConfig, optional): Configuration for the terminal. Defaults to None.
        """
        if config is None:
            self.config = TerminalConfig()
        else:
            self.config = config
        if not input_data:
            input_data = "No Input."
        self._input_data = input_data.replace("\t", " " * self.config.tab_width)
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
        self.visible_right = min(self.canvas.right + self.canvas_column_offset, self._terminal_width)
        self.visible_left = max(self.canvas.left + self.canvas_column_offset, 1)
        self._next_character_id = 0
        self._input_characters = self._decompose_input(self.config.xterm_colors, self.config.no_color)
        self._added_characters: list[EffectCharacter] = []
        self._input_characters = [
            character
            for character in self._input_characters
            if character.input_coord.row <= self.canvas.top and character.input_coord.column <= self.canvas.right
        ]
        self.character_by_input_coord: dict[Coord, EffectCharacter] = {
            (character.input_coord): character for character in self._input_characters
        }
        self._fill_characters = self._make_fill_characters()
        self._visible_characters: set[EffectCharacter] = set()
        self._frame_rate = self.config.frame_rate
        self._last_time_printed = time.time()
        self._update_terminal_state()

    def _calc_canvas_offsets(self) -> tuple[int, int]:
        """Calculate the canvas offsets based on the anchor point.

        Returns:
            tuple[int, int]: Canvas column offset, row offset
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
        """Determine the canvas dimensions using the input data dimensions, terminal dimensions, and text wrapping.

        Returns:
            tuple[int, int]: Canvas height, width.
        """
        if self.config.canvas_width > 0:
            canvas_width = self.config.canvas_width
        elif self.config.canvas_width == 0:
            canvas_width = self._terminal_width
        else:
            input_width = max([len(line.rstrip()) for line in self._input_data.splitlines()])
            if self.config.wrap_text and not self.config.ignore_terminal_dimensions:
                canvas_width = min(self._terminal_width, input_width)
            else:
                canvas_width = input_width
        if self.config.canvas_height > 0:
            canvas_height = self.config.canvas_height
        elif self.config.canvas_height == 0:
            canvas_height = self._terminal_height
        else:
            if self.config.wrap_text:
                canvas_height = len(self._wrap_lines(self._input_data.splitlines(), canvas_width))
            else:
                canvas_height = len(self._input_data.splitlines())

        return canvas_height, canvas_width

    def _get_terminal_dimensions(self) -> tuple[int, int]:
        """Gets the terminal dimensions.

        Returns:
            tuple[int, int]: terminal width and height
        """
        try:
            terminal_width, terminal_height = shutil.get_terminal_size()
        except OSError:
            # If the terminal size cannot be determined, return default values
            return 80, 24
        return terminal_width, terminal_height

    @staticmethod
    def get_piped_input() -> str:
        """Gets the piped input from stdin.

        This method checks if there is any piped input from the standard input (stdin).
        If there is no piped input, it returns an empty string.
        If there is piped input, it reads the input data from stdin and returns it as a string.

        The `sys.stdin.isatty()` check is used to determine if the program is being run interactively
        or if there is piped input. When the program is run interactively, `sys.stdin.isatty()` returns True,
        indicating that there is no piped input. In this case, the method returns an empty string.

        Returns:
            str: The piped input from stdin as a string, or an empty string if there is no piped input.
        """
        if sys.stdin.isatty():
            return ""
        return sys.stdin.read()

    def _wrap_lines(self, lines: list[str], width: int) -> list[str]:
        """
        Wraps the given lines of text to fit within the width of the canvas.

        Args:
            lines (list): The lines of text to be wrapped.
            width (int): The maximum length of a line.

        Returns:
            list: The wrapped lines of text.
        """
        wrapped_lines = []
        for line in lines:
            line = line.rstrip()
            while len(line) > width:
                wrapped_lines.append(line[:width])
                line = line[width:]
            wrapped_lines.append(line)
        return wrapped_lines

    def _decompose_input(self, use_xterm_colors: bool, no_color: bool) -> list[EffectCharacter]:
        """Decomposes the output into a list of Character objects containing the symbol and its row/column coordinates
        relative to the anchor point in the Canvas.

        Coordinates are relative to the cursor row position at the time of execution. 1,1 is the bottom left corner of the row
        above the cursor.

        Args:
            use_xterm_colors (bool): whether to convert colors to the closest XTerm-256 color

        Returns:
            list[Character]: list of EffectCharacter objects
        """

        formatted_lines = []
        if not self._input_data.strip():
            self._input_data = "No Input."
        lines = self._input_data.splitlines()
        formatted_lines = (
            self._wrap_lines(lines, self.canvas.right) if self.config.wrap_text else [line for line in lines]
        )
        input_height = len(formatted_lines)
        input_characters: list[EffectCharacter] = []
        for row, line in enumerate(formatted_lines):
            for column, symbol in enumerate(line, start=1):
                if symbol != " ":
                    character = EffectCharacter(self._next_character_id, symbol, column, input_height - row)
                    character.animation.use_xterm_colors = use_xterm_colors
                    character.animation.no_color = no_color
                    input_characters.append(character)
                    self._next_character_id += 1

        anchored_characters = self.canvas._anchor_text(input_characters, self.config.anchor_text)
        return [char for char in anchored_characters if self.canvas.coord_is_in_canvas(char._input_coord)]

    def _make_fill_characters(self) -> list[EffectCharacter]:
        """Creates a list of characters to fill the empty spaces in the canvas. The characters input_symbol is a space.
        The fill characters are added to the character_by_input_coord dictionary.

        Returns:
            list[EffectCharacter]: list of characters
        """
        fill_characters = []
        for row in range(1, self.canvas.top + 1):
            for column in range(1, self.canvas.right + 1):
                coord = Coord(column, row)
                if coord not in self.character_by_input_coord:
                    fill_char = EffectCharacter(self._next_character_id, " ", column, row)
                    fill_char.is_fill_character = True
                    fill_char.animation.use_xterm_colors = self.config.xterm_colors
                    fill_char.animation.no_color = self.config.no_color
                    fill_characters.append(fill_char)
                    self.character_by_input_coord[coord] = fill_char
                    self._next_character_id += 1
        return fill_characters

    def add_character(self, symbol: str, coord: Coord) -> EffectCharacter:
        """Adds a character to the terminal for printing. Used to create characters that are not in the input data.

        Args:
            symbol (str): symbol to add
            coord: (Coord): set character's input coordinates

        Returns:
            EffectCharacter: the character that was added
        """
        character = EffectCharacter(self._next_character_id, symbol, coord.column, coord.row)
        character.animation.use_xterm_colors = self.config.xterm_colors
        character.animation.no_color = self.config.no_color
        self._added_characters.append(character)
        self._next_character_id += 1
        return character

    def get_characters(
        self,
        *,
        input_characters: bool = True,
        fill_chars: bool = False,
        added_chars: bool = False,
        sort: CharacterSort = CharacterSort.TOP_TO_BOTTOM_LEFT_TO_RIGHT,
    ) -> list[EffectCharacter]:
        """Get a list of all EffectCharacters in the terminal with an optional sort.

        Args:
            input_characters (bool, optional): whether to include input characters. Defaults to True.
            fill_chars (bool, optional): whether to include fill characters. Defaults to False.
            added_chars (bool, optional): whether to include added characters. Defaults to False.
            sort (CharacterSort, optional): order to sort the characters. Defaults to CharacterSort.TOP_TO_BOTTOM_LEFT_TO_RIGHT.

        Returns:
            list[EffectCharacter]: list of EffectCharacters in the terminal
        """
        all_characters: list[EffectCharacter] = []
        if input_characters:
            all_characters.extend(self._input_characters)
        if fill_chars:
            all_characters.extend(self._fill_characters)
        if added_chars:
            all_characters.extend(self._added_characters)

        # default sort TOP_TO_BOTTOM_LEFT_TO_RIGHT
        all_characters.sort(key=lambda character: (-character.input_coord.row, character.input_coord.column))

        if sort is self.CharacterSort.RANDOM:
            random.shuffle(all_characters)

        elif sort in (self.CharacterSort.TOP_TO_BOTTOM_LEFT_TO_RIGHT, self.CharacterSort.BOTTOM_TO_TOP_RIGHT_TO_LEFT):
            if sort is self.CharacterSort.BOTTOM_TO_TOP_RIGHT_TO_LEFT:
                all_characters.reverse()

        elif sort in (self.CharacterSort.BOTTOM_TO_TOP_LEFT_TO_RIGHT, self.CharacterSort.TOP_TO_BOTTOM_RIGHT_TO_LEFT):
            all_characters.sort(key=lambda character: (character.input_coord.row, character.input_coord.column))
            if sort is self.CharacterSort.TOP_TO_BOTTOM_RIGHT_TO_LEFT:
                all_characters.reverse()

        elif sort in (self.CharacterSort.OUTSIDE_ROW_TO_MIDDLE, self.CharacterSort.MIDDLE_ROW_TO_OUTSIDE):
            all_characters = [
                all_characters.pop(0) if i % 2 == 0 else all_characters.pop(-1) for i in range(len(all_characters))
            ]
            if sort is self.CharacterSort.MIDDLE_ROW_TO_OUTSIDE:
                all_characters.reverse()

        return all_characters

    def get_characters_grouped(
        self,
        grouping: CharacterGroup = CharacterGroup.ROW_TOP_TO_BOTTOM,
        *,
        input_characters: bool = True,
        fill_chars: bool = False,
        added_chars: bool = False,
    ) -> list[list[EffectCharacter]]:
        """Get a list of all EffectCharacters grouped by the specified CharacterGroup grouping.

        Args:
            grouping (CharacterGroup, optional): order to group the characters. Defaults to ROW_TOP_TO_BOTTOM.
            input_characters (bool, optional): whether to include input characters. Defaults to True.
            fill_chars (bool, optional): whether to include fill characters. Defaults to False.
            added_chars (bool, optional): whether to include added characters. Defaults to False.

        Returns:
            list[list[EffectCharacter]]: list of lists of EffectCharacters in the terminal. Inner lists correspond to groups as specified in the grouping.
        """
        all_characters: list[EffectCharacter] = []
        if input_characters:
            all_characters.extend(self._input_characters)
        if fill_chars:
            all_characters.extend(self._fill_characters)
        if added_chars:
            all_characters.extend(self._added_characters)

        all_characters.sort(key=lambda character: (character.input_coord.row, character.input_coord.column))

        if grouping in (self.CharacterGroup.COLUMN_LEFT_TO_RIGHT, self.CharacterGroup.COLUMN_RIGHT_TO_LEFT):
            columns = []
            for column_index in range(self.canvas.right + 1):
                characters_in_column = [
                    character for character in all_characters if character.input_coord.column == column_index
                ]
                if characters_in_column:
                    columns.append(characters_in_column)
            if grouping == self.CharacterGroup.COLUMN_RIGHT_TO_LEFT:
                columns.reverse()
            return columns

        elif grouping in (self.CharacterGroup.ROW_BOTTOM_TO_TOP, self.CharacterGroup.ROW_TOP_TO_BOTTOM):
            rows = []
            for row_index in range(self.canvas.top + 1):
                characters_in_row = [
                    character for character in all_characters if character.input_coord.row == row_index
                ]
                if characters_in_row:
                    rows.append(characters_in_row)
            if grouping == self.CharacterGroup.ROW_TOP_TO_BOTTOM:
                rows.reverse()
            return rows
        elif grouping in (
            self.CharacterGroup.DIAGONAL_BOTTOM_LEFT_TO_TOP_RIGHT,
            self.CharacterGroup.DIAGONAL_TOP_RIGHT_TO_BOTTOM_LEFT,
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
            if grouping == self.CharacterGroup.DIAGONAL_TOP_RIGHT_TO_BOTTOM_LEFT:
                diagonals.reverse()
            return diagonals
        elif grouping in (
            self.CharacterGroup.DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT,
            self.CharacterGroup.DIAGONAL_BOTTOM_RIGHT_TO_TOP_LEFT,
        ):
            diagonals = []
            for diagonal_index in range(self.canvas.left - self.canvas.top, self.canvas.right - self.canvas.bottom + 1):
                characters_in_diagonal = [
                    character
                    for character in all_characters
                    if character.input_coord.column - character.input_coord.row == diagonal_index
                ]
                if characters_in_diagonal:
                    diagonals.append(characters_in_diagonal)
            if grouping == self.CharacterGroup.DIAGONAL_BOTTOM_RIGHT_TO_TOP_LEFT:
                diagonals.reverse()
            return diagonals
        elif grouping in (
            self.CharacterGroup.CENTER_TO_OUTSIDE_DIAMONDS,
            self.CharacterGroup.OUTSIDE_TO_CENTER_DIAMONDS,
        ):
            distance_map: dict[int, list[EffectCharacter]] = {}
            center_out = []
            for character in all_characters:
                distance = abs(character.input_coord.column - self.canvas.center.column) + abs(
                    character.input_coord.row - self.canvas.center.row
                )
                if distance not in distance_map:
                    distance_map[distance] = []
                distance_map[distance].append(character)
            for distance in sorted(
                distance_map.keys(), reverse=grouping is self.CharacterGroup.OUTSIDE_TO_CENTER_DIAMONDS
            ):
                center_out.append(distance_map[distance])
            return center_out

        else:
            raise ValueError(f"Invalid sort_order: {grouping}")

    def get_character_by_input_coord(self, coord: Coord) -> EffectCharacter | None:
        """Get an EffectCharacter by its input coordinates.

        Args:
            coord (Coord): input coordinates of the character

        Returns:
            EffectCharacter | None: the character at the specified coordinates, or None if no character is found
        """
        if coord not in self.character_by_input_coord:
            return None
        return self.character_by_input_coord[coord]

    def set_character_visibility(self, character: EffectCharacter, is_visible: bool) -> None:
        """Set the visibility of a character.

        Args:
            character (EffectCharacter): the character to set visibility for
            is_visible (bool): whether the character should be visible
        """
        character._is_visible = is_visible
        if is_visible:
            self._visible_characters.add(character)
        else:
            self._visible_characters.discard(character)

    def get_formatted_output_string(self) -> str:
        """Get the formatted output string based on the current terminal state.

        This method updates the internal terminal representation state before returning the formatted output string.

        Returns:
            str: The formatted output string.
        """
        self._update_terminal_state()
        output_string = "\n".join(self.terminal_state[::-1])
        return output_string

    def _update_terminal_state(self):
        """Update the internal representation of the terminal state with the current position
        of all visible characters.
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
        """Prepares the terminal for the effect by adding empty lines and hiding the cursor."""
        sys.stdout.write(ansitools.HIDE_CURSOR())
        sys.stdout.write(("\n" * (self.visible_top)))
        sys.stdout.write(ansitools.DEC_SAVE_CURSOR_POSITION())

    def restore_cursor(self, end_symbol: str = "\n") -> None:
        """Restores the cursor visibility and prints the end_symbol.

        Args:
            end_symbol (str, optional): The symbol to print after the effect has completed. Defaults to newline.
        """
        sys.stdout.write(ansitools.SHOW_CURSOR())
        sys.stdout.write(end_symbol)

    def print(self, output_string: str, *, enforce_frame_rate: bool = True) -> None:
        """Prints the current terminal state to stdout while preserving the cursor position.

        Args:
            output_string (str): The string to be printed.
            enforce_frame_rate (bool, optional): Whether to enforce the frame rate set in the terminal config. Defaults to True.

        Notes:
            This method includes animation timing to control the frame rate.
            If the time since the last print is less than required to limit the frame rate, the method will sleep for the remaining time
            to ensure a consistent animation speed.

        """
        if enforce_frame_rate:
            self.enforce_framerate()
        self.move_cursor_to_top()
        sys.stdout.write(output_string)
        sys.stdout.flush()

    def enforce_framerate(self):
        """Enforces the frame rate set in the terminal config by sleeping if the time since
        the last frame is shorter than the expected frame delay."""
        frame_delay = 1 / self._frame_rate
        time_since_last_print = time.time() - self._last_time_printed
        if time_since_last_print < frame_delay:
            time.sleep(frame_delay - time_since_last_print)
        self._last_time_printed = time.time()

    def move_cursor_to_top(self):
        """Restores the cursor position to the top of the canvas."""
        sys.stdout.write(ansitools.DEC_RESTORE_CURSOR_POSITION())
        sys.stdout.write(ansitools.MOVE_CURSOR_UP(self.visible_top))
