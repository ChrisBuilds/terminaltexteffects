"""Custom exceptions for handling errors related to the Terminal in the terminaltexteffects package."""

from __future__ import annotations

from typing import TYPE_CHECKING

from terminaltexteffects.utils.exceptions.base_terminaltexteffects_exception import TerminalTextEffectsError

if TYPE_CHECKING:
    from terminaltexteffects.utils.argutils import CharacterGroup, CharacterSort, ColorSort


class InvalidCharacterError(TerminalTextEffectsError):
    """Raised when a character is not owned by the receiving terminal."""

    def __init__(self, character: object) -> None:
        """Initialize an `InvalidCharacterError`.

        Args:
            character (object): Character supplied to the terminal.

        """
        self.character = character
        self.message = f"Character is not owned by this Terminal: {character!r}."
        super().__init__(self.message)


class InvalidCharacterVisibilityError(TerminalTextEffectsError):
    """Raised when a character visibility value is not a boolean."""

    def __init__(self, visibility: object) -> None:
        """Initialize an `InvalidCharacterVisibilityError`.

        Args:
            visibility (object): Visibility value supplied to the terminal.

        """
        self.visibility = visibility
        self.message = f"Character visibility must be a bool. Received: {visibility!r}."
        super().__init__(self.message)


class InvalidCharacterCoordinateError(TerminalTextEffectsError):
    """Raised when an added character is given an invalid coordinate."""

    def __init__(self, coord: object) -> None:
        """Initialize an `InvalidCharacterCoordinateError`.

        Args:
            coord (Coord | object): Coordinate supplied to the terminal.

        """
        self.coord = coord
        self.message = (
            "Character coordinates must be a Coord containing integer column and row values. "
            f"Received: {coord!r}."
        )
        super().__init__(self.message)


class InvalidCharacterGroupError(TerminalTextEffectsError):
    """Raised when an invalid character group is provided to a Terminal method.

    An InvalidCharacterGroupError is raised when a character group is provided to a Terminal method that is not a
    valid character group.

    Ref CharacterGroup.

    """

    def __init__(self, character_group: CharacterGroup | str) -> None:
        """Initialize an InvalidCharacterGroupError.

        Args:
            character_group (CharacterGroup | str): The character group provided to the Terminal method.

        """
        self.character_group = character_group
        self.message = f"Invalid character group provided: `{character_group}`. Ref CharacterGroup."
        super().__init__(self.message)


class InvalidCharacterSortError(TerminalTextEffectsError):
    """Raised when an invalid character sort is provided to a Terminal method.

    An InvalidCharacterSortError is raised when a character sort is provided to a Terminal method that is not a
    valid character sort.

    Ref CharacterSort.

    """

    def __init__(self, character_sort: CharacterSort | str) -> None:
        """Initialize an InvalidCharacterSortError.

        Args:
            character_sort (CharacterSort | str): The character sort provided to the Terminal method.

        """
        self.character_sort = character_sort
        self.message = f"Invalid character sort provided: `{character_sort}`. Ref CharacterSort."
        super().__init__(self.message)


class InvalidColorSortError(TerminalTextEffectsError):
    """Raised when an invalid color sort is provided to a Terminal method.

    An InvalidColorSortError is raised when a color sort is provided to a Terminal method that is not a
    valid color sort.

    Ref ColorSort.

    """

    def __init__(self, color_sort: ColorSort) -> None:
        """Initialize an InvalidColorSortError.

        Args:
            color_sort (ColorSort): The color sort provided to the Terminal method.

        """
        self.color_sort = color_sort
        self.message = f"Invalid color sort provided: `{color_sort}`. Ref ColorSort."
        super().__init__(self.message)


class EmptyInputError(TerminalTextEffectsError):
    """Raised when an effect has no visible input characters to render."""

    def __init__(self) -> None:
        """Initialize an EmptyInputError."""
        self.message = "Input contains no visible characters within the configured canvas."
        super().__init__(self.message)


class UnsupportedAnsiSequenceError(TerminalTextEffectsError):
    """Raised when terminal input contains ANSI/control sequences TTE does not support."""

    def __init__(self, sequence: str) -> None:
        """Initialize an UnsupportedAnsiSequenceError.

        Args:
            sequence (str): The unsupported ANSI/control sequence found in the input.

        """
        self.sequence = sequence
        self.message = (
            f"Unsupported ANSI/control sequence in input: {sequence!r}. "
            "TerminalTextEffects supports common SGR foreground/background color sequences, fetch-style CSI cursor "
            "movement, and selected DEC private mode toggles."
        )
        super().__init__(self.message)
