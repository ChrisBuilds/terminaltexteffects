"""A module for managing the terminal state and output."""

import random
import shutil
import sys
import time
from dataclasses import dataclass
from enum import Enum, auto

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils import ansitools
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass
from terminaltexteffects.utils.geometry import Coord


@dataclass
class TerminalArgs(ArgsDataClass):
    tab_width: int = ArgField(
        cmd_name=["--tab-width"],
        type_parser=arg_validators.PositiveInt.type_parser,
        metavar=arg_validators.PositiveInt.METAVAR,
        default=4,
        help="Number of spaces to use for a tab character.",
    )  # type: ignore[assignment]

    xterm_colors: bool = ArgField(
        cmd_name=["--xterm-colors"],
        default=False,
        action="store_true",
        help="Convert any colors specified in RBG hex to the closest XTerm-256 color.",
    )  # type: ignore[assignment]

    no_color: bool = ArgField(
        cmd_name=["--no-color"], default=False, action="store_true", help="Disable all colors in the effect."
    )  # type: ignore[assignment]

    no_wrap: int = ArgField(cmd_name="--no-wrap", default=False, action="store_true", help="Disable wrapping of text.")  # type: ignore[assignment]

    animation_rate: float = ArgField(
        cmd_name=["-a", "--animation-rate"],
        type_parser=arg_validators.NonNegativeFloat.type_parser,
        default=0.01,
        help="""Minimum time, in seconds, between animation steps. 
        This value does not normally need to be modified. 
        Use this to increase the playback speed of all aspects of the effect. 
        This will have no impact beyond a certain lower threshold due to the 
        processing speed of your device.""",
    )  # type: ignore[assignment]


@dataclass
class OutputArea:
    """A class for storing the output area of an effect.

    Args:
        top (int): top row of the output area
        right (int): right column of the output area
        bottom (int): bottom row of the output area. Defaults to 1.
        left (int): left column of the output area. Defaults to 1.

    """

    top: int
    right: int
    bottom: int = 1
    left: int = 1

    def __post_init__(self):
        self.center_row = max(self.top // 2, 1)
        self.center_column = max(self.right // 2, 1)
        self.center = Coord(self.center_column, self.center_row)

    def coord_is_in_output_area(self, coord: Coord) -> bool:
        """Checks whether a coordinate is within the output area.

        Args:
            coord (Coord): coordinate to check

        Returns:
            bool: whether the coordinate is within the output area
        """
        return self.left <= coord.column <= self.right and self.bottom <= coord.row <= self.top

    def random_column(self) -> int:
        """Get a random column position. Position is within the output area.

        Returns:
            int: a random column position (1 <= x <= output_area.right)"""
        return random.randint(1, self.right)

    def random_row(self) -> int:
        """Get a random row position. Position is within the output area.

        Returns:
            int: a random row position (1 <= x <= terminal.output_area.top)"""
        return random.randint(1, self.top)

    def random_coord(self, outside_scope=False) -> Coord:
        """Get a random coordinate. Coordinate is within the output area unless outside_scope is True.

        Args:
            outside_scope (bool, optional): whether the coordinate should fall outside the output area. Defaults to False.

        Returns:
            Coord: a random coordinate . Coordinate is within the output area unless outside_scope is True."""
        if outside_scope is True:
            random_coord_above = Coord(self.random_column(), self.top + 1)
            random_coord_below = Coord(self.random_column(), -1)
            random_coord_left = Coord(-1, self.random_row())
            random_coord_right = Coord(self.right + 1, self.random_row())
            return random.choice([random_coord_above, random_coord_below, random_coord_left, random_coord_right])
        else:
            return Coord(self.random_column(), self.random_row())


class Terminal:
    """A class for managing the terminal state and output."""

    class CharacterGroup(Enum):
        """An enum for grouping characters."""

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
        """An enum for sorting characters."""

        RANDOM = auto()
        TOP_TO_BOTTOM_LEFT_TO_RIGHT = auto()
        TOP_TO_BOTTOM_RIGHT_TO_LEFT = auto()
        BOTTOM_TO_TOP_LEFT_TO_RIGHT = auto()
        BOTTOM_TO_TOP_RIGHT_TO_LEFT = auto()
        OUTSIDE_ROW_TO_MIDDLE = auto()
        MIDDLE_ROW_TO_OUTSIDE = auto()

    def __init__(self, input_data: str, args: TerminalArgs):
        self.input_data = input_data.replace("\t", " " * args.tab_width)
        self.args = args
        self.width, self.height = self._get_terminal_dimensions()
        self.next_character_id = 0
        self._input_characters = self._decompose_input(args.xterm_colors, args.no_color)
        self._added_characters: list[EffectCharacter] = []
        self.input_width = max([character.input_coord.column for character in self._input_characters])
        self.input_height = max([character.input_coord.row for character in self._input_characters])
        self.output_area = OutputArea(min(self.height - 1, self.input_height), self.input_width)
        self._input_characters = [
            character
            for character in self._input_characters
            if character.input_coord.row <= self.output_area.top
            and character.input_coord.column <= self.output_area.right
        ]
        self.character_by_input_coord: dict[Coord, EffectCharacter] = {
            (character.input_coord): character for character in self._input_characters
        }
        self._fill_characters = self._make_fill_characters()
        self.visible_characters: set[EffectCharacter] = set()
        self.animation_rate = args.animation_rate
        self.last_time_printed = time.time()
        self._update_terminal_state()

        self._prep_outputarea()

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

    def _wrap_lines(self, lines: list[str]) -> list[str]:
        """
        Wraps the given lines of text to fit within the width of the terminal.

        Args:
            lines (list): The lines of text to be wrapped.

        Returns:
            list: The wrapped lines of text.
        """
        wrapped_lines = []
        for line in lines:
            while len(line) > self.width:
                wrapped_lines.append(line[: self.width])
                line = line[self.width :]
            wrapped_lines.append(line)
        return wrapped_lines

    def _decompose_input(self, use_xterm_colors: bool, no_color: bool) -> list[EffectCharacter]:
        """Decomposes the output into a list of Character objects containing the symbol and its row/column coordinates
        relative to the input display location.

        Coordinates are relative to the cursor row position at the time of execution. 1,1 is the bottom left corner of the row
        above the cursor.

        Args:
            use_xterm_colors (bool): whether to convert colors to the closest XTerm-256 color

        Returns:
            list[Character]: list of EffectCharacter objects
        """
        formatted_lines = []
        if not self.input_data.strip():
            self.input_data = "No Input."
        lines = self.input_data.splitlines()
        formatted_lines = self._wrap_lines(lines) if not self.args.no_wrap else [line[: self.width] for line in lines]
        input_height = len(formatted_lines)
        input_characters = []
        for row, line in enumerate(formatted_lines):
            for column, symbol in enumerate(line):
                if symbol != " ":
                    character = EffectCharacter(self.next_character_id, symbol, column + 1, input_height - row)
                    character.animation.use_xterm_colors = use_xterm_colors
                    character.animation.no_color = no_color
                    input_characters.append(character)
                    self.next_character_id += 1
        return input_characters

    def _make_fill_characters(self) -> list[EffectCharacter]:
        """Creates a list of characters to fill the empty spaces in the output area. The characters input_symbol is a space.
        The fill characters are added to the character_by_input_coord dictionary.

        Returns:
            list[EffectCharacter]: list of characters
        """
        fill_characters = []
        for row in range(1, self.output_area.top + 1):
            for column in range(1, self.output_area.right + 1):
                coord = Coord(column, row)
                if coord not in self.character_by_input_coord:
                    fill_char = EffectCharacter(self.next_character_id, " ", column, row)
                    fill_characters.append(fill_char)
                    self.character_by_input_coord[coord] = fill_char
                    self.next_character_id += 1
        return fill_characters

    def add_character(self, symbol: str, coord: Coord) -> EffectCharacter:
        """Adds a character to the terminal for printing. Used to create characters that are not in the input data.

        Args:
            symbol (str): symbol to add
            coord: (Coord): set character's input coordinates

        Returns:
            EffectCharacter: the character that was added
        """
        character = EffectCharacter(self.next_character_id, symbol, coord.column, coord.row)
        character.animation.use_xterm_colors = self.args.xterm_colors
        character.animation.no_color = self.args.no_color
        self._added_characters.append(character)
        self.next_character_id += 1
        return character

    def _update_terminal_state(self):
        """Update the internal representation of the terminal state with the current position
        of all visible characters.
        """
        rows = [[" " for _ in range(self.output_area.right)] for _ in range(self.output_area.top)]
        for character in sorted(self.visible_characters, key=lambda c: c.layer):
            row = character.motion.current_coord.row - 1
            column = character.motion.current_coord.column - 1
            if 0 <= row < self.output_area.top and 0 <= column < self.output_area.right:
                rows[row][column] = character.symbol
        terminal_state = ["".join(row) for row in rows]
        self.terminal_state = terminal_state

    def _prep_outputarea(self) -> None:
        """Prepares the terminal for the effect by adding empty lines above."""
        sys.stdout.write(ansitools.HIDE_CURSOR())
        print("\n" * self.output_area.top)

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
            for column_index in range(self.output_area.right + 1):
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
            for row_index in range(self.output_area.top + 1):
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
            for diagonal_index in range(self.output_area.top + self.output_area.right + 1):
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
            for diagonal_index in range(
                self.output_area.left - self.output_area.top, self.output_area.right - self.output_area.bottom + 1
            ):
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
                distance = abs(character.input_coord.column - self.output_area.center.column) + abs(
                    character.input_coord.row - self.output_area.center.row
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
            self.visible_characters.add(character)
        else:
            self.visible_characters.discard(character)

    def print(self):
        """Prints the current terminal state to stdout while preserving the cursor position."""
        self._update_terminal_state()
        time_since_last_print = time.time() - self.last_time_printed
        if time_since_last_print < self.animation_rate:
            time.sleep(self.animation_rate - time_since_last_print)
        output = "\n".join(self.terminal_state[::-1])
        sys.stdout.write(ansitools.DEC_SAVE_CURSOR_POSITION())
        sys.stdout.write(ansitools.MOVE_CURSOR_UP(self.output_area.top))
        sys.stdout.write(ansitools.MOVE_CURSOR_TO_COLUMN(1))
        sys.stdout.write(output)
        sys.stdout.write(ansitools.DEC_RESTORE_CURSOR_POSITION())
        sys.stdout.flush()
        self.last_time_printed = time.time()
