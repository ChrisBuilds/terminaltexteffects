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
the cell it came from, so text mounted there, on a body that hasn't moved, looks exactly like the input.

## In TTE

The Axes example draws the three axes as lines of dots, mounts the input text on a plane, and turns them all
together to an angled view and back. These are the lines that place the text:

```python
self.text = self.space.body()  # No shape: a plain frame of reference.
characters = [c for c in self.terminal.get_characters() if c.input_symbol != " "]
self.text.add_chars(characters, self.text.text_plane(characters))
```

??? example "axes.py"

    Save it in your community effects directory as `axes.py`.

    ```python
    --8<-- "docs/effectguide/examples/3d/axes/axes.py"
    ```

```bash
tte --input-file concept_input.txt --canvas-width 80 --canvas-height 24 --anchor-text c axes
```

![The red X, green Y and blue Z axes turn with the text plane, then everything returns to rest](../../img/effectguide/axes_demo.webp)

At rest, the Z axis points straight at you, so all its dots land on the center cell. Once the view turns, you can
see it come out of the screen.

- `self.space.body()` with no shape is a plain **frame of reference**: a position, orientation and scale to hang
  anchors on.
- `body.anchor(x, y, z)` is a point in the body's own coordinates. It moves and turns with the body.
- `text_plane(characters)` makes one anchor per character, placed so each one meets its character's input cell
  **at the body's pose when you call it**. It works backward from the body's current rotation, position and scale.
  The Axes example builds it on a body that hasn't moved yet, so the text meets its input cells whenever the body is
  back at its starting pose.
- `add_chars(characters, anchors)` mounts each character on its anchor. From then on, the anchor decides where the
  character is drawn.

### Rest and pose

A body's **pose** is its whole transform: rotation, position and scale. **Rest** is only the rotation part: the
orientation a body is created in, with no turn applied. `turn_to_rest()` and `settle()` bring the rotation back to
rest, but leave position and scale alone.

So text built with `text_plane` lands on its input cells when the body returns to the pose it had when the anchors
were made. Build the anchors first, on an unmoved body, then apply the starting transforms: the text is then home
whenever the body is back at rest, at the origin and at scale 1. Build them on a body already turned 30 degrees, and
the text reads correctly at that turn instead, and moves off its input cells at rest.

## Normals for anchors

`body.anchor(x, y, z, normal="z")` gives the anchor a **normal**: the direction its surface faces, in the body's own
coordinates. Any axis name or `(x, y, z)` direction works. The normal is separate from the anchor's position and
turns with the body. It's what lets a mount report how it faces the camera and the light:

```python
front = card.anchor(0, 0, 0, normal="z")  # Faces the viewer while the card is at rest.
plain = card.anchor(0, 0, 0)  # No normal.
```

- With a normal, `mount.facing`, `mount.facing_amount` and `mount.light` follow the turning surface, and
  `hide_when_facing_away=True` can hide the character while its side faces away (see [Depth](depth.md)).
- Without one, the mount always reports `facing=True`, `facing_amount=1` and `light=1`, however the body turns.
  Lighting scenes and backface hiding then have nothing to follow.

`text_plane` gives every anchor the normal of its plane, so a card of text lights and hides like a card. The layouts
below give normals pointing out of the shape. Anchors you make yourself have none unless you pass one.

## Anchor layouts

A body can lay out anchors for you. Each layout returns a list of anchors to pass to `add_chars` with the same number
of characters:

| Layout | Anchors | Normals | Choose it for |
| --- | --- | --- | --- |
| `text_plane(characters)` | One per character, on its input cell at the current pose | The plane's | Text that must land back on its input cells |
| `surface(count)` | About `count`, spread evenly over the shape | Out of each face | Covering a shape with characters in no particular order |
| `vertices()` | One per corner | Away from the center | Marking a shape's corners |
| `edges(count)` | About `count`, spread along the edges | Away from the center | Outlining a shape with characters |
| `ring(count, radius, axis="y")` | `count`, evenly around a circle | Outward | Orbits, halos and carousels; needs no shape |
| `wrap(characters)` | One per character, the text wrapped once around | Out of the surface | Text that reads around a `Cylinder` or `Sphere`, row by row |

`surface`, `vertices` and `edges` need a body with a shape, and `wrap` needs a `Cylinder` or `Sphere`. A shaped body
carries anchors whether or not it is drawn. This mounts the input text around an undrawn cylinder, so only the
letters show:

```python
from terminaltexteffects.engine.space3d import Cylinder

characters = [c for c in self.terminal.get_characters() if c.input_symbol != " "]
drum = self.space.body(Cylinder(radius=16, height=12))
drum.add_chars(characters, drum.wrap(characters), hide_when_facing_away=True)
drum.spin("y", turns=1, frames=240)
```

`surface(len(characters))` would scatter the same characters over the drum instead, with no reading order. `wrap`
mounts each character on its own anchor, so it keeps its colors and scenes and can be released afterward. A
`Textured` look, by contrast, draws the shape's surface out of text, resampled cell by cell (see
[Texture mapping](textures.md#mounted-text-or-textured-surface)). For the full signatures, see the
[`Body` reference](../../engine/space3d.md).

## Under the hood

A point is a [`Vec3`](../../engine/utils/geometry3d.md). `text_plane` lifts each input cell into 3D with
`camera.cell_to_world(coord)`, the exact inverse of `camera.project(point)` on the z = 0 plane:

```python
from terminaltexteffects.utils.geometry3d import Vec3

point = self.space.camera.cell_to_world(character.input_coord)  # Vec3(x, y, 0.0)
cell = self.space.camera.project(point).coord  # Back to character.input_coord.
```

`body.world_point(local)` turns a point in the body's coordinates into world coordinates, using the body's current
position, orientation and scale. `text_plane` runs the other way: it takes each lifted point and undoes the body's
current transform to find the local anchor, which is why the result depends on the pose at the time of the call.

## At cell resolution

- World y is measured in columns, but the canvas counts rows. A row is about two columns tall, so moving a body up
  by 10 moves it up about 5 rows.
- Anchors snap to the nearest cell. Two anchors less than a cell apart land in the same cell, and only one of their
  characters shows there.
- The canvas center can fall between two cells when the canvas has an even width or height, so a shape at the
  origin can look half a cell off center.
