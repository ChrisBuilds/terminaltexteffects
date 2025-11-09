"""Use Prims algorithm to generated a tree.

The returned cell list is based on the order in which cells are linked into the tree.

This various of Prims is unweighted.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from terminaltexteffects.engine.terminal import Coord
    from terminaltexteffects.utils.spanningtree.cell import Cell
    from terminaltexteffects.utils.spanningtree.grid import Grid


def generate_cell_list(grid: Grid, starting_coord: Coord | None) -> list[Cell]:
    """Generate ordered list of cells using an unweighted Prims algorithm.

    Args:
        grid (Grid): Grid
        starting_coord (Coord | None): Starting cell for the tree. If not provided, a random
            cell will be used.

    Returns:
        list[Cell]: List of cells in link-order.

    """
    cell_list = []
    cell_set = set()
    total_unlinked_cells = len(list(grid.each_cell()))
    if starting_coord is not None:
        cell = grid.get_cell((starting_coord.row, starting_coord.column))
    else:
        cell = grid.random_cell()
    cell = grid.random_cell()
    edge_cells = []
    edge_cells.append(cell)

    while edge_cells:
        working_cell = edge_cells.pop(random.randrange(len(edge_cells)))
        neighbors = [neighbor for neighbor in grid.get_neighbors(working_cell).values() if neighbor]
        unlinked_neighbors = [neighbor for neighbor in neighbors if not neighbor.links]
        if unlinked_neighbors:
            next_cell = unlinked_neighbors.pop(random.randrange(len(unlinked_neighbors)))
            grid.link_cells(working_cell, next_cell)
            if working_cell not in cell_set:
                cell_list.append(working_cell)
            if next_cell not in cell_set:
                cell_list.append(next_cell)
            cell_set.update({working_cell, next_cell})
            total_unlinked_cells -= 1
            if unlinked_neighbors:
                edge_cells.append(working_cell)
            unlinked_neighbors = [n for n in grid.get_neighbors(next_cell).values() if n and not n.links]
            if unlinked_neighbors:
                edge_cells.append(next_cell)
    return cell_list
