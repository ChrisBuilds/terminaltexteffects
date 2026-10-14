"""Keep input ANSI colors attached to editable text.

Text loaded into the TUI may carry SGR color sequences, such as the output of `ls --color` or `fastfetch`. The editor
shows the plain text, while this module keeps one optional `CellStyle` per character, carries the styles across
edits, and rebuilds colored input for the effect. This module does not import Textual.
"""

from __future__ import annotations

import difflib
import typing
from dataclasses import dataclass

from terminaltexteffects.engine.terminal_input import VirtualScreenParser

if typing.TYPE_CHECKING:
    from terminaltexteffects.utils.graphics import Color


@dataclass(frozen=True)
class CellStyle:
    """Foreground, background, and bold attributes parsed from one input character.

    Attributes:
        fg (Color | None): Foreground color.
        bg (Color | None): Background color.
        bold (bool): Whether the character is bold.

    """

    fg: Color | None = None
    bg: Color | None = None
    bold: bool = False

    def sgr(self) -> str:
        """Return the SGR sequence that applies this style after a reset."""
        codes = []
        if self.bold:
            codes.append("1")
        for prefix, color in (("38", self.fg), ("48", self.bg)):
            if color is None:
                continue
            if color.xterm_color is not None:
                codes.append(f"{prefix};5;{color.xterm_color}")
            else:
                red, green, blue = color.rgb_ints
                codes.append(f"{prefix};2;{red};{green};{blue}")
        return f"\x1b[{';'.join(codes)}m" if codes else ""


StyleList = list["CellStyle | None"]


def has_ansi(text: str) -> bool:
    """Return whether `text` contains escape sequences."""
    return "\x1b" in text


def parse_colored_text(text: str, tab_width: int = 4) -> tuple[str, StyleList]:
    """Return the plain text laid out by `text`'s escape sequences and one style per plain character.

    Cursor movement is resolved the same way the effect engine resolves it, so the plain text matches the layout
    the effect would show. Newlines and gap-filling spaces have no style.

    Raises:
        UnsupportedAnsiSequenceError: If `text` contains a sequence the engine cannot parse.

    """
    parsed = VirtualScreenParser(tab_width=tab_width).parse(text)
    chars: list[str] = []
    styles: StyleList = []
    for row_index, row in enumerate(parsed.character_rows):
        if row_index:
            chars.append("\n")
            styles.append(None)
        column = 0
        for character in row:
            if character.column < column:
                continue
            gap = character.column - column
            chars.append(" " * gap)
            styles.extend([None] * gap)
            chars.append(character.symbol)
            style = CellStyle(character.fg_color, character.bg_color, character.bold)
            styles.append(style if style != CellStyle() else None)
            column = character.column + character.cell_width
    # Rows end at their last retained character, so restore trailing blank lines up to the final cursor row.
    trailing_rows = parsed.final_cursor_row - (len(parsed.character_rows) - 1)
    if trailing_rows > 0:
        chars.append("\n" * trailing_rows)
        styles.extend([None] * trailing_rows)
    return "".join(chars), styles


def carry_styles(
    old_text: str,
    old_styles: StyleList,
    new_text: str,
    insert_style: CellStyle | None = None,
) -> StyleList:
    """Return styles for `new_text` that keep the styles of characters unchanged since `old_text`.

    Replaced characters keep the styles of the characters they replace, position by position. Inserted characters
    take the style of the character before them on the same line, as typing extends a colored word. When
    `insert_style` is given, inserted and replaced characters take it instead.
    """
    new_styles: StyleList = [None] * len(new_text)
    matcher = difflib.SequenceMatcher(None, old_text, new_text, autojunk=False)
    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if tag == "equal":
            new_styles[new_start:new_end] = old_styles[old_start:old_end]
        elif tag in ("replace", "insert"):
            replaced = old_styles[old_start:old_end] if tag == "replace" else []
            for offset, index in enumerate(range(new_start, new_end)):
                if new_text[index] == "\n":
                    continue
                if insert_style is not None:
                    new_styles[index] = insert_style
                elif offset < len(replaced):
                    new_styles[index] = replaced[offset]
                elif index and new_text[index - 1] != "\n":
                    new_styles[index] = new_styles[index - 1]
    return new_styles


def paint(
    text: str,
    styles: StyleList,
    start: int,
    end: int,
    update: typing.Callable[[CellStyle | None], CellStyle | None],
) -> StyleList:
    """Return `styles` with `update` applied to the styles of the characters of `text` from `start` to `end`.

    Newlines keep no style. Styles that `update` leaves empty become `None`.
    """
    painted = list(styles)
    for index in range(max(0, start), min(end, len(text))):
        if text[index] == "\n":
            continue
        style = update(painted[index])
        painted[index] = style if style != CellStyle() else None
    return painted


def to_ansi(text: str, styles: StyleList) -> str:
    """Return `text` with SGR sequences that apply `styles`, resetting at each line end."""
    parts: list[str] = []
    current: CellStyle | None = None
    for character, style in zip(text, styles):
        if character == "\n":
            if current is not None:
                parts.append("\x1b[0m")
                current = None
            parts.append("\n")
            continue
        if style != current:
            if current is not None:
                parts.append("\x1b[0m")
            if style is not None:
                parts.append(style.sgr())
            current = style
        parts.append(character)
    if current is not None:
        parts.append("\x1b[0m")
    return "".join(parts)
