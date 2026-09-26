# SynthGrid

SynthGrid divides the canvas into cells that are approximately square after accounting for terminal character
proportions. Cell widths and heights differ by at most one position; leftover space is spread across the grid.
The layout aims for about five cells along the longer visual axis and uses smaller cells on narrow canvases.
Cells normally have at least four columns and two rows. Canvases smaller than those dimensions use a single
cell along the affected axis.

Grid lines overlay the cells, so every input character remains part of the dissolve animation. Intersections
share one grid character, and lines that would obscure tiny cells are omitted. A canvas that fits in one cell,
including a single-character canvas, starts dissolving immediately without drawing a grid.

![Demo](../img/effects_demos/synthgrid_demo.gif)

## Quick Start

``` py title="synthgrid.py"
from terminaltexteffects.effects.effect_synthgrid import SynthGrid

effect = SynthGrid("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_synthgrid
