# Terminal

*Module*: `terminaltexteffects.engine.terminal`

!!! info "New in 0.16.0"

    `CharacterOrder`, spiral sorting, grid grouping, and `clock()` are available on development `main` and are not
    in the published 0.15.0 package.

## Character Orders

`CharacterOrder` unifies spatial groups and individual character sorts. Both terminal methods accept
`order=...` and use immutable input coordinates:

```python
from terminaltexteffects import CharacterOrder, Terminal

terminal = Terminal("abc\ndef")
groups = terminal.get_characters_grouped(order=CharacterOrder.ROW_TOP_TO_BOTTOM)
characters = terminal.get_characters(order=CharacterOrder.ROW_TOP_TO_BOTTOM)
backward = terminal.get_characters(order=CharacterOrder.ROW_TOP_TO_BOTTOM, reverse=True)
```

Spatial orders preserve their group boundaries; individual orders such as spirals produce singleton
groups. Flattening the grouped form gives the flat traversal. Row groups and individual row traversals
remain separate choices because they have different activation batches despite matching flat order.
`CharacterOrder.is_grouped` identifies spatial orders.

`reverse=True` reverses the complete traversal. In grouped output it reverses both the group sequence
and each group's internal sequence, preserving membership. `serpentine=True` reverses alternate spatial
groups before optional global reversal. Random ordering is sampled once per call; reversal does not
reshuffle it. Separate random calls require the same random state to produce matching output forms.

`canvas_only=True` excludes off-canvas input coordinates; `False` includes them. When omitted, spatial
orders clip to the canvas and individual orders include the complete selected inventory, independently
of the output form. This preserves legacy selection behavior while allowing explicit overrides. All four
input, inner-fill, outer-fill, and added-character selection flags remain available.

Existing `CharacterGroup`, `CharacterSort`, `sort=...`, and `grouping=...` remain supported. Pass either
`order` or the compatibility keyword, not both. The no-argument defaults remain row groups from top to
bottom for `get_characters_grouped()` and top-to-bottom, left-to-right for `get_characters()`.

## Spiral Sorting

Use `get_characters(order=...)` to order characters in a rectangular spiral from the outside inward:

```python
from terminaltexteffects import Terminal
from terminaltexteffects import CharacterOrder

terminal = Terminal("YourTextHere")
characters = terminal.get_characters(order=CharacterOrder.SPIRAL_CLOCKWISE)
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
for both direction options. With `reverse=True`, spirals follow the same path outward;
this differs from choosing the other clockwise/counterclockwise option.

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
Pass `reverse=True` to reverse both the cell sequence and each cell's internal sequence.

## Effect Clock

Effects that measure a phase in seconds should read `terminal.clock()` instead of calling `time.time()` or
`time.monotonic()` directly:

```python
self.phase_start = self.terminal.clock()
...
if self.terminal.clock() - self.phase_start >= self.config.phase_seconds:
    self.phase = "next"
```

During live output, `clock()` returns `time.monotonic()`. When `tte --export` renders frames ahead of time,
the terminal uses a frame clock that advances by `1 / frame_rate` per frame, so a phase lasts the same
number of frames as it would live and recordings are reproducible with `--seed`. When an effect reads wall-clock
time directly, a recorded phase runs for that many seconds of rendering time instead, so its length in frames
depends on rendering speed and is usually far longer than intended.

## Row Caching

!!! info "New in 0.16.0"

    `enable_row_cache()` is available on development `main` and is not in the published 0.15.0 package.

An effect can call `self.terminal.enable_row_cache()` to reuse formatted rows until their characters change.
The engine tracks coordinates, animation visuals, visibility, layers, and direct `formatted_symbol` assignments.
Wide characters use the existing width-aware renderer; caching resumes when all visible characters are single-cell.
Existing motion and animation references, paths, and scenes remain valid when caching is enabled.

Measure before enabling caching (see [Performance Testing](../../performance.md)): tracking and row membership consume
extra memory, and frequent changes can reduce the benefit. Cache activation changes rendering work without changing
effect options, scheduling, or random decisions.

These built-in effects enable caching automatically within the input ranges where it measured faster:

| Effect | Activation requirements |
| --- | --- |
| Matrix | Canvas at least 4 rows with at least 256 cells. |
| Print | Text at least 16 columns by 4 rows, with at least 256 input characters. |
| Pour | Up/down pouring; text at least 64 by 12, with at least 768 characters and three-quarter occupancy. |
| BouncyBalls | Text at least 64 by 16, with at least 1,024 characters and three-quarter occupancy. |
| ErrorCorrect | Text at least 8 by 5, with at least 80 input characters. |
| SynthGrid | Visible canvas at least 8 by 4, including sparse text. |
| Rain | Text at least 80 by 24, with at least 1,680 characters and seven-eighths occupancy. |

All but Matrix also require single-cell input symbols, and the text-based gates require the text bounds to fit within
the visible canvas. Occupancy is the input-character count divided by the area of the text bounds; fill and helper
characters do not contribute. These checks run before effect build and helper allocation. Later wide visual changes
still use the width-aware fallback. Smaller inputs and horizontal Pour keep the default renderer.

To compare Matrix runs reproducibly, advance its wall-clock-based rain phase with the same simulated clock in both
runs and verify frame counts and output hashes.

::: terminaltexteffects.engine.terminal.Terminal
