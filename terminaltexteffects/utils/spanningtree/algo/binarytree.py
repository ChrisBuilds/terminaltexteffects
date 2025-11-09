from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from terminaltexteffects.utils.spanningtree.cell import Cell
    from terminaltexteffects.utils.spanningtree.grid import Grid


def generate_maze(grid: Grid) -> list[Cell]:
    unlinked_cells = set(grid.each_cell())
    cell_list = []

    for cell in grid.each_cell():
        neighbors = grid.get_neighbors(cell)
        neighbors.pop("south", None)
        neighbors.pop("west", None)
        if neighbors:
            neighbor = random.choice(list(neighbors.values()))
            if neighbor:
                grid.link_cells(cell, neighbor)
                unlinked_cells.discard(neighbor)
                unlinked_cells.discard(cell)
                cell_list.append(cell)
                cell_list.append(neighbor)
    return cell_list
