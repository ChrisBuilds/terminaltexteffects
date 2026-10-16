# Space and Coordinates

Before you can place anything in 3D, you need to know where the axes point and what the units are. TTE uses one
convention everywhere, chosen so that the input text sits exactly where it does in 2D.

## The idea

- The **origin** is the center of the canvas.
- **x** points right, **y** points up and **z** points toward you, out of the screen.
- One **unit** is the width of one terminal column. Positions, sizes and distances are all in columns, including
  heights: a shape 10 units tall is 10 columns tall, which is about 5 rows (see [Tall cells](tall-cells.md)).
- **Angles** are in degrees in `Space3D`, and **axes** can be named `"x"`, `"y"`, `"z"` or `"diagonal"`, or given
  as any `(x, y, z)` direction.

![The canvas lies on the z = 0 plane with the origin at its center. x points right, y up, and z out toward the camera](../../img/effectguide/3d/world_axes.webp)

Think of the canvas as a window in the z = 0 plane, with the camera standing in front of it on the z axis, looking
straight through. Anything behind the window (negative z) is farther from you; anything in front of it (positive z)
is nearer.

The input text lies flat on the plane where z is 0. With the camera at rest, every point on that plane lands back on
the cell it came from, so text mounted on that plane at rest looks exactly like the input.

## In TTE

The Axes example draws the three axes as lines of dots, mounts the input text on a plane, and turns them all
together to an angled view and back. Save it as `axes.py`:

```python title="axes.py"
--8<-- "docs/effectguide/examples/3d/axes/axes.py"
```

```bash
tte --input-file concept_input.txt --canvas-width 80 --canvas-height 24 --anchor-text c axes
```

![The red X, green Y and blue Z axes turn with the text plane, then everything returns to rest](../../img/effectguide/axes_demo.webp)

At rest, the Z axis points straight at you, so all its dots land on the center cell. Once the view turns, you can
see it come out of the screen.

- `self.space.body()` with no shape is a plain **frame of reference**: a position and orientation to hang anchors
  on.
- `body.anchor(x, y, z)` is a point in the body's own coordinates. It moves and turns with the body.
- `text_plane(characters)` makes one anchor per character, placed so each one meets its character's input cell
  while the body is at rest.
- `add_chars(characters, anchors)` mounts each character on its anchor. From then on, the anchor decides where the
  character is drawn.

## Under the hood

A point is a [`Vec3`](../../engine/utils/geometry3d.md). `text_plane` lifts each input cell into 3D with
`camera.cell_to_world(coord)`, the exact inverse of `camera.project(point)` on the z = 0 plane:

```python
from terminaltexteffects.utils.geometry3d import Vec3

point = self.space.camera.cell_to_world(character.input_coord)  # Vec3(x, y, 0.0)
cell = self.space.camera.project(point).coord  # Back to character.input_coord.
```

`body.world_point(local)` turns a point in the body's coordinates into world coordinates, using the body's current
position, orientation and scale.

## At cell resolution

- World y is measured in columns, but the canvas counts rows. A row is about two columns tall, so moving a body up
  by 10 moves it up about 5 rows.
- Anchors snap to the nearest cell. Two anchors less than a cell apart land in the same cell, and only one of their
  characters shows there.
- The canvas center can fall between two cells when the canvas has an even width or height, so a shape at the
  origin can look half a cell off center.
