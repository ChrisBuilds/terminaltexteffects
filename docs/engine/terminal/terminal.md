# Terminal

*Module*: `terminaltexteffects.engine.terminal`

## Spiral Sorting

Use `get_characters(sort=...)` to order characters in a rectangular spiral from the outside inward:

```python
from terminaltexteffects import Terminal
from terminaltexteffects.utils.argutils import CharacterSort

terminal = Terminal("YourTextHere")
characters = terminal.get_characters(sort=CharacterSort.SPIRAL_CLOCKWISE)
```

| Clockwise | Counterclockwise | Starting corners |
| --- | --- | --- |
| `SPIRAL_CLOCKWISE` | `SPIRAL_COUNTER_CLOCKWISE` | Top-left |
| `SPIRAL_CLOCKWISE_DOUBLE` | `SPIRAL_COUNTER_CLOCKWISE_DOUBLE` | Top-left and bottom-right |
| `SPIRAL_CLOCKWISE_QUAD` | `SPIRAL_COUNTER_CLOCKWISE_QUAD` | Top-left, top-right, bottom-right, bottom-left |

Spirals use the bounding box of the selected characters' immutable input coordinates. Each rectangular ring
is completed before the next begins, and empty coordinates are skipped. Multiple arms are interleaved by
the number of steps from their starting corners, with ties resolved in the corner order listed above.
Characters reached by more than one arm are returned once; distinct characters at the same coordinate
retain their selection order. On a final single row or column, arms move inward from their endpoints
for both direction options.

All character selection flags are supported, including fill characters and added characters outside the canvas.
Moving a character does not change its sort position, and wide symbols are sorted once at their input coordinate.

## Grid Grouping

Use `get_characters_grouped_by_grid()` with a `geometry.GridLayout` to collect characters into rectangular cells:

```python
from terminaltexteffects import Terminal, geometry

terminal = Terminal("YourTextHere")
canvas = terminal.canvas
grid = geometry.find_balanced_grid(canvas.left, canvas.bottom, canvas.right, canvas.top)
groups = terminal.get_characters_grouped_by_grid(grid)
```

Groups use immutable input coordinates and are returned bottom-to-top, then left-to-right. Empty cells and
characters outside the grid or canvas are omitted. The method supports the same input, fill, and added-character
selection flags as `get_characters_grouped()` and preserves selection order within each cell.

::: terminaltexteffects.engine.terminal.Terminal
