"""Parse terminal input into a styled virtual-screen representation.

The parser in this module is intentionally independent from `Terminal` and
`EffectCharacter` allocation. A parser instance contains only immutable configuration;
every `parse()` call creates fresh state and returns a reusable parsed value object.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import ClassVar

from terminaltexteffects.utils.exceptions import UnsupportedAnsiSequenceError
from terminaltexteffects.utils.graphics import Color
from terminaltexteffects.utils.terminal_text import get_symbol_cell_width

_ScreenCoord = tuple[int, int]


@dataclass(frozen=True, slots=True)
class ParsedCharacter:
    """A styled character retained on the parsed virtual screen."""

    character_id: int
    symbol: str
    row: int
    column: int
    cell_width: int
    fg_color: Color | None
    bg_color: Color | None
    bold: bool


@dataclass(frozen=True, slots=True)
class ParsedInput:
    """Immutable output from one virtual-screen parse."""

    character_rows: tuple[tuple[ParsedCharacter, ...], ...]
    line_widths: tuple[int, ...]
    character_id_count: int
    final_cursor_row: int
    final_cursor_column: int
    color_frequencies: tuple[tuple[Color, int], ...]


@dataclass(slots=True)
class _ParserState:
    """Mutable state owned by exactly one `VirtualScreenParser.parse()` call."""

    fg_color: Color | None = None
    bg_color: Color | None = None
    bold: bool = False
    standard_fg_parameter: int | None = None
    cursor_row: int = 0
    cursor_column: int = 0
    max_row: int = 0
    max_column: int = 0
    next_character_id: int = 0
    screen: dict[_ScreenCoord, ParsedCharacter] = field(default_factory=dict)
    screen_cell_owners: dict[_ScreenCoord, _ScreenCoord] = field(default_factory=dict)
    occupied_coords: set[_ScreenCoord] = field(default_factory=set)
    color_frequencies: dict[Color, int] = field(default_factory=dict)


class VirtualScreenParser:
    """Parse text, supported SGR colors, and fetch-style cursor movement."""

    _ANSI_ESCAPE_SEQUENCE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"(?:\x1b\][^\x07]*(?:\x07|\x1b\\))|(?:\x1b\[[0-?]*[ -/]*[@-~])|(?:\x1b.)",
    )
    _CSI_SEQUENCE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"\x1b\[([0-?]*)([ -/]*)([@-~])")
    _MAX_CSI_PARAMETER = 9_999_999
    _MAX_VIRTUAL_SCREEN_DIMENSION = 100_000
    _MAX_VIRTUAL_SCREEN_CELLS = 1_000_000
    _SUPPORTED_PRIVATE_MODE_SEQUENCES = frozenset({"\x1b[?25h", "\x1b[?25l", "\x1b[?7h", "\x1b[?7l"})

    def __init__(self, *, tab_width: int) -> None:
        """Initialize the parser with an immutable tab width.

        Args:
            tab_width (int): Number of terminal cells between tab stops.

        Raises:
            ValueError: If `tab_width` is not a positive non-boolean integer.

        """
        if isinstance(tab_width, bool) or not isinstance(tab_width, int) or tab_width < 1:
            msg = "tab_width must be a positive integer"
            raise ValueError(msg)
        self._tab_width = tab_width

    @classmethod
    def _parse_csi_parameters(cls, parameters: str, sequence: str) -> list[int]:
        """Parse bounded CSI parameters, treating omitted values as zero."""
        if any(char not in "0123456789;" for char in parameters):
            raise UnsupportedAnsiSequenceError(sequence)
        if not parameters:
            return []
        parameter_fields = parameters.split(";")
        max_parameter_digits = len(str(cls._MAX_CSI_PARAMETER))
        if any(len(parameter) > max_parameter_digits for parameter in parameter_fields):
            raise UnsupportedAnsiSequenceError(sequence)
        parsed_parameters = [int(parameter) if parameter else 0 for parameter in parameter_fields]
        if any(parameter > cls._MAX_CSI_PARAMETER for parameter in parsed_parameters):
            raise UnsupportedAnsiSequenceError(sequence)
        return parsed_parameters

    @staticmethod
    def _default_parameter(parameters: list[int]) -> int:
        """Return the first CSI parameter, defaulting zero or omission to one."""
        if not parameters:
            return 1
        return max(parameters[0], 1)

    def _apply_sgr_sequence(self, sequence: str, state: _ParserState) -> None:
        """Apply supported SGR parameters to `state`."""
        parameters = self._parse_csi_parameters(sequence[2:-1], sequence)
        if not parameters:
            parameters = [0]
        param_index = 0
        while param_index < len(parameters):
            parameter = parameters[param_index]
            if parameter == 0:
                state.fg_color = state.bg_color = None
                state.bold = False
                state.standard_fg_parameter = None
            elif parameter == 1:
                state.bold = True
                if state.standard_fg_parameter is not None:
                    state.fg_color = Color(state.standard_fg_parameter - 30 + 8)
            elif parameter == 22:
                state.bold = False
                if state.standard_fg_parameter is not None:
                    state.fg_color = Color(state.standard_fg_parameter - 30)
            elif parameter == 39:
                state.fg_color = None
                state.standard_fg_parameter = None
            elif parameter == 49:
                state.bg_color = None
            elif 30 <= parameter <= 37:
                state.fg_color = Color(parameter - 30 + (8 if state.bold else 0))
                state.standard_fg_parameter = parameter
            elif 90 <= parameter <= 97:
                state.fg_color = Color(parameter - 90 + 8)
                state.standard_fg_parameter = None
            elif 40 <= parameter <= 47:
                state.bg_color = Color(parameter - 40)
            elif 100 <= parameter <= 107:
                state.bg_color = Color(parameter - 100 + 8)
            elif parameter in (38, 48):
                color, consumed_parameters = self._parse_extended_color(parameters, param_index, sequence)
                if parameter == 38:
                    state.fg_color = color
                    state.standard_fg_parameter = None
                else:
                    state.bg_color = color
                param_index += consumed_parameters
            else:
                raise UnsupportedAnsiSequenceError(sequence)
            param_index += 1

    @staticmethod
    def _parse_extended_color(parameters: list[int], param_index: int, sequence: str) -> tuple[Color, int]:
        """Parse an indexed or RGB extended color and return its consumed tail length."""
        if param_index + 1 >= len(parameters):
            raise UnsupportedAnsiSequenceError(sequence)
        color_mode = parameters[param_index + 1]
        if color_mode == 5:
            if param_index + 2 >= len(parameters):
                raise UnsupportedAnsiSequenceError(sequence)
            color_code = parameters[param_index + 2]
            if color_code > 255:
                raise UnsupportedAnsiSequenceError(sequence)
            return Color(color_code), 2
        if color_mode == 2:
            if param_index + 4 >= len(parameters):
                raise UnsupportedAnsiSequenceError(sequence)
            color_channels = parameters[param_index + 2 : param_index + 5]
            if any(channel > 255 for channel in color_channels):
                raise UnsupportedAnsiSequenceError(sequence)
            color_code = "".join(f"{channel:02X}" for channel in color_channels)
            return Color(color_code), 4
        raise UnsupportedAnsiSequenceError(sequence)

    def _apply_cursor_sequence(self, sequence: str, state: _ParserState) -> None:
        """Apply a supported cursor movement sequence to `state`."""
        csi_match = self._CSI_SEQUENCE_PATTERN.fullmatch(sequence)
        if not csi_match:
            raise UnsupportedAnsiSequenceError(sequence)
        parameters_text, intermediates, final_byte = csi_match.groups()
        if intermediates or parameters_text.startswith("?"):
            raise UnsupportedAnsiSequenceError(sequence)
        parameters = self._parse_csi_parameters(parameters_text, sequence)
        if final_byte == "A":
            self._require_parameter_count(parameters, 1, sequence)
            state.cursor_row -= self._default_parameter(parameters)
        elif final_byte == "B":
            self._require_parameter_count(parameters, 1, sequence)
            state.cursor_row += self._default_parameter(parameters)
        elif final_byte == "C":
            self._require_parameter_count(parameters, 1, sequence)
            state.cursor_column += self._default_parameter(parameters)
        elif final_byte == "D":
            self._require_parameter_count(parameters, 1, sequence)
            state.cursor_column -= self._default_parameter(parameters)
        elif final_byte == "E":
            self._require_parameter_count(parameters, 1, sequence)
            state.cursor_row += self._default_parameter(parameters)
            state.cursor_column = 0
        elif final_byte == "F":
            self._require_parameter_count(parameters, 1, sequence)
            state.cursor_row -= self._default_parameter(parameters)
            state.cursor_column = 0
        elif final_byte == "G":
            self._require_parameter_count(parameters, 1, sequence)
            state.cursor_column = self._default_parameter(parameters) - 1
        elif final_byte in ("H", "f"):
            self._require_parameter_count(parameters, 2, sequence)
            state.cursor_row = self._default_parameter(parameters) - 1
            state.cursor_column = (parameters[1] if len(parameters) > 1 and parameters[1] else 1) - 1
        else:
            raise UnsupportedAnsiSequenceError(sequence)
        state.cursor_row = max(state.cursor_row, 0)
        state.cursor_column = max(state.cursor_column, 0)

    @staticmethod
    def _require_parameter_count(parameters: list[int], maximum: int, sequence: str) -> None:
        """Reject a CSI sequence with more than `maximum` parameters."""
        if len(parameters) > maximum:
            raise UnsupportedAnsiSequenceError(sequence)

    @classmethod
    def _update_virtual_screen_bounds(cls, sequence: str, state: _ParserState) -> None:
        """Record and validate the largest cursor-addressable virtual screen."""
        prospective_max_row = max(state.max_row, state.cursor_row)
        prospective_max_column = max(state.max_column, state.cursor_column)
        if (
            prospective_max_row >= cls._MAX_VIRTUAL_SCREEN_DIMENSION
            or prospective_max_column >= cls._MAX_VIRTUAL_SCREEN_DIMENSION
            or (prospective_max_row + 1) * (prospective_max_column + 1) > cls._MAX_VIRTUAL_SCREEN_CELLS
        ):
            raise UnsupportedAnsiSequenceError(sequence)
        state.max_row = prospective_max_row
        state.max_column = prospective_max_column

    @staticmethod
    def _remove_screen_character(state: _ParserState, owner: _ScreenCoord) -> None:
        """Remove an overwritten character and each terminal cell that it owned."""
        character = state.screen.pop(owner)
        for offset in range(character.cell_width):
            state.screen_cell_owners.pop((owner[0], owner[1] + offset), None)

    def _write_symbol(self, symbol: str, cell_width: int, state: _ParserState) -> None:
        """Write one symbol at the cursor, applying terminal-cell overwrite rules."""
        symbol_coords = [(state.cursor_row, state.cursor_column + offset) for offset in range(cell_width)]
        for symbol_coord in symbol_coords:
            previous_owner = state.screen_cell_owners.get(symbol_coord)
            if previous_owner is not None:
                self._remove_screen_character(state, previous_owner)

        coord = symbol_coords[0]
        state.occupied_coords.update(symbol_coords)
        character_id = state.next_character_id
        state.next_character_id += 1
        if symbol != " " or state.fg_color is not None or state.bg_color is not None:
            character = ParsedCharacter(
                character_id=character_id,
                symbol=symbol,
                row=state.cursor_row,
                column=state.cursor_column,
                cell_width=cell_width,
                fg_color=state.fg_color,
                bg_color=state.bg_color,
                bold=state.bold,
            )
            state.screen[coord] = character
            for symbol_coord in symbol_coords:
                state.screen_cell_owners[symbol_coord] = coord

        state.max_row = max(state.max_row, state.cursor_row)
        state.max_column = max(state.max_column, state.cursor_column + cell_width - 1)
        state.cursor_column += cell_width

    @staticmethod
    def _build_result(state: _ParserState) -> ParsedInput:
        """Build an immutable sparse-row result from final parser state."""
        rectangle_size = (state.max_row + 1) * (state.max_column + 1)
        character_id_count = state.next_character_id + rectangle_size - len(state.occupied_coords)
        if not state.screen:
            return ParsedInput(
                character_rows=((),),
                line_widths=(1,),
                character_id_count=character_id_count,
                final_cursor_row=state.cursor_row,
                final_cursor_column=state.cursor_column,
                color_frequencies=tuple(state.color_frequencies.items()),
            )

        last_character_row = max(row for row, _ in state.screen)
        entries_by_row: dict[int, list[ParsedCharacter]] = {}
        for (screen_row, _), character in state.screen.items():
            entries_by_row.setdefault(screen_row, []).append(character)

        character_rows: list[tuple[ParsedCharacter, ...]] = []
        line_widths: list[int] = []
        for screen_row in range(last_character_row + 1):
            character_row = tuple(sorted(entries_by_row.get(screen_row, []), key=lambda character: character.column))
            character_rows.append(character_row)
            for character in character_row:
                for color in (character.fg_color, character.bg_color):
                    if color is not None:
                        state.color_frequencies[color] = state.color_frequencies.get(color, 0) + 1
            line_widths.append(
                max((character.column + character.cell_width for character in character_row), default=0),
            )
        return ParsedInput(
            character_rows=tuple(character_rows),
            line_widths=tuple(line_widths),
            character_id_count=character_id_count,
            final_cursor_row=state.cursor_row,
            final_cursor_column=state.cursor_column,
            color_frequencies=tuple(state.color_frequencies.items()),
        )

    def parse(self, input_data: str) -> ParsedInput:
        """Parse `input_data` using fresh virtual-screen and style state.

        Args:
            input_data (str): Text and supported terminal sequences to parse.

        Returns:
            ParsedInput: Sparse final screen layout and parse metadata.

        Raises:
            UnsupportedAnsiSequenceError: If input contains an unsupported control sequence.

        """
        state = _ParserState()
        char_index = 0
        while char_index < len(input_data):
            symbol = input_data[char_index]
            if symbol == "\x1b":
                sequence_match = self._ANSI_ESCAPE_SEQUENCE_PATTERN.match(input_data, char_index)
                if not sequence_match:
                    raise UnsupportedAnsiSequenceError(symbol)
                sequence = sequence_match.group(0)
                if not sequence.startswith("\x1b["):
                    raise UnsupportedAnsiSequenceError(sequence)
                csi_match = self._CSI_SEQUENCE_PATTERN.fullmatch(sequence)
                if not csi_match:
                    raise UnsupportedAnsiSequenceError(sequence)
                final_byte = csi_match.group(3)
                if final_byte == "m":
                    self._apply_sgr_sequence(sequence, state)
                elif sequence not in self._SUPPORTED_PRIVATE_MODE_SEQUENCES:
                    self._apply_cursor_sequence(sequence, state)
                    self._update_virtual_screen_bounds(sequence, state)
                char_index = sequence_match.end()
                continue
            if symbol == "\n":
                state.cursor_row += 1
                state.cursor_column = 0
                state.max_row = max(state.max_row, state.cursor_row)
                char_index += 1
                continue
            if symbol == "\r":
                state.cursor_column = 0
                char_index += 1
                continue

            codepoint = ord(symbol)
            if symbol != "\t" and (codepoint < 0x20 or 0x7F <= codepoint <= 0x9F):
                raise UnsupportedAnsiSequenceError(symbol)
            if symbol == "\t":
                symbol = " "
                cell_width = 1
                symbol_repetitions = self._tab_width - (state.cursor_column % self._tab_width)
            else:
                cell_width = get_symbol_cell_width(symbol)
                symbol_repetitions = 1
            for _ in range(symbol_repetitions):
                self._write_symbol(symbol, cell_width, state)
            char_index += 1

        return self._build_result(state)
