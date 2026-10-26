# Tall Cells

Terminal cells are not square. A typical cell is about twice as tall as it is wide, so a shape drawn with one cell per
unit in both directions comes out twice as tall as it should. TTE corrects for this in the camera, so you can work in
plain columns and still get round spheres and square cubes.

## The idea

Measured in pixels, a row is roughly two columns tall. If a 16 unit cube were drawn 16 columns wide and 16 rows tall,
it would look like a tower. To look like a cube on screen, it must be 16 columns wide and about 8 rows tall.

![A cell is about twice as tall as wide. Eight units drawn one cell per unit make a tall box; counting rows as two units makes a square](../../img/effectguide/3d/tall_cells.webp)

The camera does this by counting each row as `row_scale` units of height, 2 by default
(`geometry.TERMINAL_ROW_SCALE`). Everything above the camera works in columns, as if cells were square. Only the
final step, from world space to canvas rows, divides heights by 2.

## In TTE

The Cells example turns two bodies side by side. On the left is a 16 unit cube. On the right is a box twice as tall,
16 by 32 by 16, which is how the cube would look if the camera counted each row as one unit:

```python
self.world.body(Cube(16), at=(-20, 0, 0)).draw(Shaded())
self.world.body(Box(16, 32, 16), at=(20, 0, 0)).draw(Shaded())
```

??? example "cells.py"

    Save it in your community effects directory as `cells.py`.

    ```python
    --8<-- "docs/effectguide/examples/3d/cells/cells.py"
    ```

```bash
tte --input-file concept_input.txt --canvas-width 80 --canvas-height 24 --anchor-text c cells
```

![A correct cube on the left, and a cube twice as tall on the right](../../img/effectguide/cells_demo.webp)

A world has one camera, so the example shows the uncorrected cube as a box built twice as tall. Setting
`world.camera.row_scale = 1` would draw the whole scene that way. You never need it in a real effect.

## Under the hood

[`Camera`](../../engine/utils/geometry3d.md) has a `row_scale` field. `project` divides the y offset by it, and
`cell_to_world` multiplies by it, so the two stay exact inverses:

```python
row = center_row + point.y * scale / row_scale
```

Line symbols for wireframes use the same scale. `geometry3d.line_symbol` multiplies the row change by `row_scale`
before measuring an edge's angle, so a 45 degree edge on screen is drawn with `/` and not `|`.

## At cell resolution

- Vertical detail is half as fine as horizontal detail. A sphere 16 columns wide is only 8 rows tall, so its top
  and bottom edges are coarse. Wider shapes hide this best.
- In the default orthographic view, moving a body by 1 unit in y moves it half a row, so slow vertical motion steps
  once every two units. A turned camera or perspective changes screen displacement. Horizontal
  motion steps every unit and looks smoother.
- Turning doesn't favor either axis. Text on a face turning about x and text turning about y both shrink by the
  cosine of the angle, so at 60 degrees each shows half its rows or half its columns. The row correction already
  allowed for tall cells when the text was lifted into 3D.
- Fonts vary, so the real ratio is somewhere around 1.8 to 2.2. TTE uses 2 because it's close for common fonts.
