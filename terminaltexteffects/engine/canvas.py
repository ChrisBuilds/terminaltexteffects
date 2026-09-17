"""Define the logical content area in which a terminal text effect operates.

`Canvas` is the effect's coordinate workspace: it defines the rows and columns used
to lay out input text, position effect characters, and select coordinates. It is not
the terminal viewport. `Terminal` separately determines which part of this workspace
is visible on the physical terminal and clips rendered output to that visible region.
"""

from __future__ import annotations

import random
import typing
from typing import Literal

from terminaltexteffects.utils.geometry import Coord

if typing.TYPE_CHECKING:
    from terminaltexteffects.engine.base_character import EffectCharacter


class Canvas:
    """Represent the logical content area of a terminal text effect.

    The canvas is the bounded coordinate workspace in which an effect lays out its
    input text and positions characters. `Terminal` calculates its bounds from the
    input dimensions, physical terminal dimensions, and `TerminalConfig`, then uses
    separate visible bounds as the viewport that clips output to the physical terminal.
    A canvas can therefore describe more content than is currently visible.

    Canvas bounds are positive, inclusive, and immutable after construction. The text
    bounds describe the anchored input region within that workspace. For even canvas
    or text dimensions, center coordinates identify the lower central cell.

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

    Raises:
        ValueError: If either origin bound is non-positive or the bounds are inverted.

    """

    __hash__ = None  # pyright: ignore[reportAssignmentType]

    def __init__(self, top: int, right: int, bottom: int = 1, left: int = 1) -> None:
        """Initialize validated canvas bounds and empty text-boundary values."""
        if bottom < 1 or left < 1:
            msg = "Canvas bottom and left bounds must be positive."
            raise ValueError(msg)
        if top < bottom or right < left:
            msg = "Canvas top and right bounds must not be less than bottom and left bounds."
            raise ValueError(msg)
        self._top = top
        self._right = right
        self._bottom = bottom
        self._left = left
        self._reset_text_bounds()

    @property
    def top(self) -> int:
        """Return the inclusive top row."""
        return self._top

    @property
    def right(self) -> int:
        """Return the inclusive right column."""
        return self._right

    @property
    def bottom(self) -> int:
        """Return the inclusive bottom row."""
        return self._bottom

    @property
    def left(self) -> int:
        """Return the inclusive left column."""
        return self._left

    @property
    def width(self) -> int:
        """Return the number of columns in the inclusive bounds."""
        return self.right - self.left + 1

    @property
    def height(self) -> int:
        """Return the number of rows in the inclusive bounds."""
        return self.top - self.bottom + 1

    @property
    def center_row(self) -> int:
        """Return the lower central row."""
        return self.bottom + ((self.height - 1) // 2)

    @property
    def center_column(self) -> int:
        """Return the lower central column."""
        return self.left + ((self.width - 1) // 2)

    @property
    def center(self) -> Coord:
        """Return the lower central coordinate."""
        return Coord(self.center_column, self.center_row)

    def __eq__(self, other: object) -> bool:
        """Return whether another canvas has the same bounds."""
        if not isinstance(other, Canvas):
            return NotImplemented
        return (self.top, self.right, self.bottom, self.left) == (
            other.top,
            other.right,
            other.bottom,
            other.left,
        )

    def __repr__(self) -> str:
        """Return the constructor-style representation used by the former dataclass API."""
        return f"Canvas(top={self.top}, right={self.right}, bottom={self.bottom}, left={self.left})"

    def _anchor_text(
        self,
        characters: list[EffectCharacter],
        anchor: Literal["n", "ne", "e", "se", "s", "sw", "w", "nw", "c"],
    ) -> list[EffectCharacter]:
        """Anchors the text within the canvas based on the specified anchor point.

        Args:
            characters (list[EffectCharacter]): Characters to reposition within the canvas. An empty list produces
                an empty text region.
            anchor (Literal["n", "ne", "e", "se", "s", "sw", "w", "nw", "c"]): Anchor point for the text
                within the Canvas.

        Returns:
            list[EffectCharacter]: List of characters anchored within the canvas. Only returns characters with
                coordinates within the canvas after anchoring.

        """
        if not characters:
            self._reset_text_bounds()
            return []

        # translate coordinate based on anchor within the canvas
        input_left = 1
        input_right = max(
            character._input_coord.column + character.animation.current_character_visual.cell_width - 1
            for character in characters
        )
        input_bottom = 1
        input_top = max(character._input_coord.row for character in characters)
        input_center_column = input_left + ((input_right - input_left) // 2)
        input_center_row = input_bottom + ((input_top - input_bottom) // 2)

        if anchor in ("s", "n", "c"):
            column_delta = self.center_column - input_center_column
        elif anchor in ("se", "e", "ne"):
            column_delta = self.right - input_right
        else:
            column_delta = self.left - input_left
        if anchor in ("w", "e", "c"):
            row_delta = self.center_row - input_center_row
        elif anchor in ("nw", "n", "ne"):
            row_delta = self.top - input_top
        else:
            row_delta = self.bottom - input_bottom

        for character in characters:
            current_coord = character.input_coord
            anchored_coord = Coord(
                current_coord.column + column_delta,
                current_coord.row + row_delta,
            )
            character._input_coord = anchored_coord
            character.motion.set_coordinate(anchored_coord)

        characters = [
            character
            for character in characters
            if self.coord_is_in_canvas(character.input_coord)
            and character.input_coord.column + character.animation.current_character_visual.cell_width - 1 <= self.right
        ]

        if not characters:
            self._reset_text_bounds()
            return []

        # get text dimensions, centers, and extents
        text_left = min(character.input_coord.column for character in characters)
        text_right = max(
            character.input_coord.column + character.animation.current_character_visual.cell_width - 1
            for character in characters
        )
        text_top = max(character.input_coord.row for character in characters)
        text_bottom = min(character.input_coord.row for character in characters)
        text_center_row = text_bottom + ((text_top - text_bottom) // 2)
        text_center_column = text_left + ((text_right - text_left) // 2)
        self.text_left = text_left
        self.text_right = text_right
        self.text_top = text_top
        self.text_bottom = text_bottom
        self.text_width = text_right - text_left + 1
        self.text_height = text_top - text_bottom + 1
        self.text_center_row = text_center_row
        self.text_center_column = text_center_column
        self.text_center = Coord(text_center_column, text_center_row)
        return characters

    def _reset_text_bounds(self) -> None:
        """Set the text bounds to the empty-region sentinel values."""
        self.text_left = self.text_right = 0
        self.text_top = self.text_bottom = 0
        self.text_width = self.text_height = 0
        self.text_center_row = self.text_center_column = 0
        self.text_center = Coord(0, 0)

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
        return (
            self.text_width > 0
            and self.text_height > 0
            and self.text_left <= coord.column <= self.text_right
            and self.text_bottom <= coord.row <= self.text_top
        )

    def _require_nonempty_text_boundary(self) -> None:
        """Raise `ValueError` if the canvas has no text boundary."""
        if not self.text_width or not self.text_height:
            msg = "Cannot select a random position from an empty text boundary."
            raise ValueError(msg)

    def random_column(self, *, within_text_boundary: bool = False) -> int:
        """Get a random column position within the canvas.

        Args:
            within_text_boundary (bool, optional): If True, the column will be limited to the text boundary. Otherwise,
                it can be anywhere within the canvas. Defaults to False.

        Returns:
            int: a random column position within the canvas

        Raises:
            ValueError: If `within_text_boundary` is `True` and the text boundary is empty.

        """
        if within_text_boundary:
            self._require_nonempty_text_boundary()
            return random.randint(self.text_left, self.text_right)
        return random.randint(self.left, self.right)

    def random_row(self, *, within_text_boundary: bool = False) -> int:
        """Get a random row position within the canvas.

        Args:
            within_text_boundary (bool, optional): If True, the row will be limited to the text boundary. Otherwise,
                it can be anywhere within the canvas. Defaults to False.

        Returns:
            int: a random row position within the canvas

        Raises:
            ValueError: If `within_text_boundary` is `True` and the text boundary is empty.

        """
        if within_text_boundary:
            self._require_nonempty_text_boundary()
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

        Raises:
            ValueError: If `within_text_boundary` is `True`, `outside_scope` is `False`, and the text boundary is empty.

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
