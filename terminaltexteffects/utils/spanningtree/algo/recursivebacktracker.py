from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from terminaltexteffects.utils.spanningtree.cell import Cell
    from terminaltexteffects.utils.spanningtree.grid import Grid


def generate_maze(grid: Grid) -> list[Cell]:
    cell = grid.random_cell()
    stack = [cell]
    cell_list = []
    cell_set = set()

    while stack:
        neighbors = [neighbor for neighbor in grid.get_neighbors(cell).values() if neighbor]
        unvisited_neighbors = [neighbor for neighbor in neighbors if not neighbor.links]
        if unvisited_neighbors:
            next_cell = random.choice(unvisited_neighbors)
            grid.link_cells(cell, next_cell)
            if cell not in cell_set:
                cell_list.append(cell)
            if next_cell not in cell_set:
                cell_list.append(next_cell)
            cell_set.update({cell, next_cell})
            stack.append(next_cell)
            cell = next_cell
        else:
            stack.pop()
            if stack:
                cell = stack[-1]
    return cell_list
