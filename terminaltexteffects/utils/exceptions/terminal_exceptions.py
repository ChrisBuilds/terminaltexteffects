"""Custom exceptions for handling errors related to the Terminal in the terminaltexteffects package."""

from __future__ import annotations

from typing import TYPE_CHECKING

from terminaltexteffects.utils.exceptions.base_terminaltexteffects_exception import TerminalTextEffectsError

if TYPE_CHECKING:
    from terminaltexteffects.engine.terminal import Terminal


class InvalidCharacterGroupError(TerminalTextEffectsError):
    """Raised when an invalid character group is provided to a Terminal method.

    An InvalidCharacterGroupError is raised when a character group is provided to a Terminal method that is not a
    valid character group.

    Ref Terminal.CharacterGroup.

    """

    def __init__(self, character_group: Terminal.CharacterGroup | str) -> None:
        """Initialize an InvalidCharacterGroupError.

        Args:
            character_group (Terminal.CharacterGroup | str): The character group provided to the Terminal method.

        """
        self.character_group = character_group
        self.message = f"Invalid character group provided: `{character_group}`. Ref Terminal.CharacterGroup."
        super().__init__(self.message)


class InvalidCharacterSortError(TerminalTextEffectsError):
    """Raised when an invalid character sort is provided to a Terminal method.

    An InvalidCharacterSortError is raised when a character sort is provided to a Terminal method that is not a
    valid character sort.

    Ref Terminal.CharacterSort.

    """

    def __init__(self, character_sort: Terminal.CharacterSort | str) -> None:
        """Initialize an InvalidCharacterSortError.

        Args:
            character_sort (Terminal.CharacterSort | str): The character sort provided to the Terminal method.

        """
        self.character_sort = character_sort
        self.message = f"Invalid character sort provided: `{character_sort}`. Ref Terminal.CharacterSort."
        super().__init__(self.message)


class InvalidColorSortError(TerminalTextEffectsError):
    """Raised when an invalid color sort is provided to a Terminal method.

    An InvalidColorSortError is raised when a color sort is provided to a Terminal method that is not a
    valid color sort.

    Ref Terminal.ColorSort.

    """

    def __init__(self, color_sort: Terminal.ColorSort) -> None:
        """Initialize an InvalidColorSortError.

        Args:
            color_sort (Terminal.ColorSort): The color sort provided to the Terminal method.

        """
        self.color_sort = color_sort
        self.message = f"Invalid color sort provided: `{color_sort}`. Ref Terminal.ColorSort."
        super().__init__(self.message)
