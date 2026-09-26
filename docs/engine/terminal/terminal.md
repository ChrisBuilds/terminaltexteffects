# Terminal

*Module*: `terminaltexteffects.engine.terminal`

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
