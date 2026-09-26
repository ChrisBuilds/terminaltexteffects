# Geometry

*Module*: `terminaltexteffects.utils.geometry`

## Balanced Grids

`find_balanced_grid(left, bottom, right, top)` returns a `GridLayout` covering inclusive bounds. It accounts for
terminal character height when choosing row and column counts, then divides each axis so cell sizes differ by
at most one position. `target_cells`, `min_cell_width`, and `min_cell_height` control the preferred size.

The layout's `column_boundaries` and `row_boundaries` include an exclusive final boundary, one beyond the
canvas edge. Each cell includes its lower boundaries and excludes its upper boundaries. For example,
an 80-column by 24-row canvas produces five columns of cells and three rows, with cells measuring 16 by 8.

::: terminaltexteffects.utils.geometry
