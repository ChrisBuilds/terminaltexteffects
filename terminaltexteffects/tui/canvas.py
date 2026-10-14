"""Canvas geometry for the TUI's canvas outline.

Effects draw in an area of the text area that leaves a one-cell margin for the canvas outline, on a canvas placed
inside that area by `anchor_canvas` the same way the engine places it inside the terminal. These helpers find the
area, locate the canvas in top-down coordinates, say which outline edges can be dragged for an anchor, and turn a
dragged edge position into a canvas dimension. This module does not import Textual.
"""

from __future__ import annotations

import typing
from dataclasses import dataclass

Edge = typing.Literal["left", "right", "top", "bottom"]


@dataclass(frozen=True)
class CanvasRect:
    """The canvas position in the text area, with rows counted from the top.

    Attributes:
        left (int): First canvas column.
        top (int): First canvas row.
        width (int): Canvas width.
        height (int): Canvas height.

    """

    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        """Return the column just right of the canvas."""
        return self.left + self.width

    @property
    def bottom(self) -> int:
        """Return the row just below the canvas."""
        return self.top + self.height


def canvas_rect(area_width: int, area_height: int, width: int, height: int, anchor: str) -> CanvasRect:
    """Return where a `width` by `height` canvas sits in the text area for `anchor`.

    This mirrors the engine's canvas offsets, which count rows from the bottom.
    """
    if anchor in ("n", "s", "c"):
        left = (area_width - width) // 2
    elif anchor in ("ne", "e", "se"):
        left = area_width - width
    else:
        left = 0
    if anchor in ("w", "e", "c"):
        top = area_height - height - (area_height - height) // 2
    elif anchor in ("sw", "s", "se"):
        top = area_height - height
    else:
        top = 0
    return CanvasRect(left, top, width, height)


def canvas_area(width: int, height: int, anchor: str) -> CanvasRect:
    """Return the part of a `width` by `height` text area that effects draw in for `anchor`.

    One cell is left free beyond each edge that moves with the anchor, so the canvas outline, which sits just outside
    the canvas, stays visible and draggable even when the canvas fills the area.
    """
    edges = draggable_edges(anchor)
    left = 1 if "left" in edges else 0
    top = 1 if "top" in edges else 0
    right = 1 if "right" in edges else 0
    bottom = 1 if "bottom" in edges else 0
    return CanvasRect(left, top, max(1, width - left - right), max(1, height - top - bottom))


def draggable_edges(anchor: str) -> frozenset[Edge]:
    """Return the canvas edges that move when the canvas is resized with `anchor`."""
    edges: set[Edge] = set()
    if "w" in anchor:
        edges.add("right")
    elif "e" in anchor:
        edges.add("left")
    else:
        edges.update(("left", "right"))
    if "n" in anchor:
        edges.add("bottom")
    elif "s" in anchor:
        edges.add("top")
    else:
        edges.update(("top", "bottom"))
    return frozenset(edges)


def dragged_size(edge: Edge, position: int, area_size: int, anchor: str) -> int:
    """Return the canvas dimension that puts the outline of `edge` at `position`.

    `position` is the column or row of the outline, which sits just outside the canvas. The result is clamped to
    the range from 1 to `area_size`.
    """
    centered = (edge in ("left", "right") and "w" not in anchor and "e" not in anchor) or (
        edge in ("top", "bottom") and "n" not in anchor and "s" not in anchor
    )
    if edge in ("right", "bottom"):
        size = 2 * position - area_size if centered else position
    else:
        size = area_size - 2 * (position + 1) if centered else area_size - (position + 1)
    return max(1, min(area_size, size))


def edges_at(rect: CanvasRect, x: int, y: int, edges: typing.Iterable[Edge]) -> set[Edge]:
    """Return which of `edges` have their outline at cell `x`, `y`, including the corners they share."""
    hits: set[Edge] = set()
    within_rows = rect.top - 1 <= y <= rect.bottom
    within_columns = rect.left - 1 <= x <= rect.right
    for edge in edges:
        if (
            (edge == "right" and x == rect.right and within_rows)
            or (edge == "left" and x == rect.left - 1 and within_rows)
            or (edge == "bottom" and y == rect.bottom and within_columns)
            or (edge == "top" and y == rect.top - 1 and within_columns)
        ):
            hits.add(edge)
    return hits
