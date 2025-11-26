"""Custom exceptions for handling errors related to the Terminal in the terminaltexteffects package."""

from __future__ import annotations

from terminaltexteffects.utils.argutils import CharacterGroup, CharacterSort, ColorSort
from terminaltexteffects.utils.exceptions.base_terminaltexteffects_exception import TerminalTextEffectsError


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
