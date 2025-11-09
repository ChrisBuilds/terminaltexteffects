from __future__ import annotations

import random
from collections.abc import Generator
from typing import Optional
from terminaltexteffects.engine.terminal import Canvas
from terminaltexteffects.utils.spanningtree.cell import Cell


class Grid:
    def __init__(
        self,
        canvas: Canvas,
    ) -> None:
        """Create a new grid with the given width and height.

        :param width: the number of columns in the grid
        :param height: the number of rows in the grid
        :param mask_string: mask to apply
        """
        self.canvas = canvas
        self.cells: dict[tuple[int, int], Cell] = {}
        self.prepare_grid()
        self.configure_cells()

    def prepare_grid(self) -> None:
        """Create a dictionary of Cell objects, where the dictionary key is a tuple of the row and column, and
        the value is the Cell object.
        """
        for row in range(1, self.canvas.top + 1):
            for col in range(1, self.canvas.right + 1):
                cell = Cell(row, col)
                self.cells[(row, col)] = cell

    def configure_cells(self) -> None:
        """For each cell in the grid, set the neighbors of that cell to the cells that are adjacent to it."""
        for cell in self.cells.values():
            row = cell.row
            col = cell.column
            adjacent_cell_coordinates = {
                "north": (row - 1, col),
                "south": (row + 1, col),
                "west": (row, col - 1),
                "east": (row, col + 1),
            }
            for direction, coordinates in adjacent_cell_coordinates.items():
                neighbor = self.get_cell(coordinates)
                if neighbor:
                    cell.neighbors[direction] = neighbor
                else:
                    cell.neighbors[direction] = None

    def get_cell(self, cell: tuple[int, int]) -> Optional[Cell]:
        """Given cell coordinates, return the cell object if valid coordinates, else None.

        :param cell: a tuple of the form (row, column)
        :return: The cell object
        """
        if cell in self.cells:
            return self.cells[cell]
        return None

    def get_neighbors(self, cell: Cell, existing_only: bool = True) -> dict[str, Optional[Cell]]:
        """Given a cell, return a list of its neighboring cells.

        :param cell: the cell to get the neighbors of
        :param ignore_mask: return masked and unmasked neighbors. Defaults to False.
        :param existing_only: if True, only return direction:Cell pair if neighbor exists. Defaults to True.
        :return: A dict of {str,Cell} neighbors.
        """
        neighbors = {}
        for direction, neighbor in cell.neighbors.items():
            if existing_only and not neighbor:
                continue
            neighbors[direction] = neighbor
        return neighbors

    def link_cells(self, cell_a: Cell, cell_b: Cell, bidi: bool = True) -> None:
        """Link cells and update visual grid to show link.

        :param cell_a: cell from which the link starts
        :param cell_b: cell to which the link occurs
        :param bidi: If True, the link is bidirectional, defaults to True (optional)
        """
        cell_a.link(cell_b, bidi=bidi)

    def unlink_cells(self, cell_a: Cell, cell_b: Cell, bidi: bool = True) -> None:
        cell_a.unlink(cell_b, bidi=bidi)

    def random_cell(self) -> Cell:
        """Return a random cell from the grid.

        Returns:
            Cell: Cell

        """
        cell = random.choice(list(self.cells.values()))
        return cell

    def size(self) -> int:
        """Return the number of cells in the grid.
        :return: Number of cells in the grid
        """
        return self.canvas.top * self.canvas.right

    def each_row(self, bottom_up: bool = False) -> Generator[list[Cell], None, None]:
        """Yield one row of the grid at a time as a list.

        :param bottom_up: If True, the cells are traversed in bottom-up order, defaults to False (optional)
        """
        if bottom_up:
            range_gen = range(self.canvas.top + 1 - 1, -1, -1)
        else:
            range_gen = range(self.canvas.top + 1)
        for row in range_gen:
            yield [cell for col in range(self.canvas.right + 1) if (cell := self.cells.get((row, col), None))]

    def each_column(self) -> Generator[list[Cell], None, None]:
        """Yield one column of the grid at a time as a list.

        :param ignore_mask: If True, include masked cells in the list of cells, defaults to False (optional)
        """
        for column in range(self.canvas.right + 1):
            yield [self.cells[(row, column)] for row in range(self.canvas.top + 1)]

    def each_cell(self) -> Generator[Cell, None, None]:
        """Return a generator that yields a cell at a time.
        :param ignore_mask: If True, include masked cells, defaults to False (optional)
        """
        for row in range(1, self.canvas.top + 1):
            for col in range(1, self.canvas.right + 1):
                yield self.cells[(row, col)]
