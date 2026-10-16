# Camera and Projection

The camera decides how 3D points become cells. Its one setting you'll change most is how strong the perspective is:
how much nearer things grow and farther things shrink.

## The idea

The camera sits on the +z axis, looking back at the origin. To draw a point, it **projects** it: it finds where the
line from the point to the camera crosses the screen.

- With **perspective**, things farther away look smaller, and parallel lines running away from you converge. A point
  at depth `d` from the camera is scaled by `distance / d`, so the z = 0 plane keeps its size, nearer points grow
  and farther ones shrink.
- An **orthographic** view drops the scaling. Everything keeps its size whatever its depth, like a technical drawing.
  It's flat, but it's also stable: nothing swells as it turns toward you.

![Side view: with perspective, rays from an object converge on the camera, so its drawn size shrinks as it moves away; with an orthographic view the rays are parallel and the size stays the same](../../img/effectguide/3d/projection.webp)

Perspective strength comes from the camera's distance. A camera close to the scene makes small changes in depth
look large. A distant camera barely changes sizes at all.

![The same near and far objects drawn with perspective 0, 1 and 2: the far object shrinks more as the camera comes closer](../../img/effectguide/3d/perspective_strength.webp)

## In TTE

The Lens example places three cubes, each 26 columns to the right of and 60 columns farther away than the one
before. Save it as `lens.py`:

```python title="lens.py"
--8<-- "docs/effectguide/examples/3d/lens/lens.py"
```

=== "perspective 0"

    ```bash
    tte --input-file concept_input.txt --canvas-width 80 --canvas-height 24 --anchor-text c lens --perspective 0
    ```

    ![Three cubes the same size, evenly spaced](../../img/effectguide/lens_0_demo.webp)

=== "perspective 1"

    ```bash
    tte --input-file concept_input.txt --canvas-width 80 --canvas-height 24 --anchor-text c lens
    ```

    ![The farther cubes are smaller and closer to the center](../../img/effectguide/lens_1_demo.webp)

=== "perspective 2"

    ```bash
    tte --input-file concept_input.txt --canvas-width 80 --canvas-height 24 --anchor-text c lens --perspective 2
    ```

    ![The farthest cube is tiny and near the center](../../img/effectguide/lens_2_demo.webp)

`Space3D(terminal, perspective=...)` sets the strength:

- `1`, the default, is a natural perspective. The camera is 120 columns from the origin.
- Larger values move the camera closer. `2` puts it 60 columns away, which exaggerates depth.
- `0` is orthographic.

## Under the hood

[`geometry3d.Camera`](../../engine/utils/geometry3d.md) does the projection. `Space3D` makes one centered on the
canvas, and you can read it as `space.camera`:

```python
projected = self.space.camera.project(point)  # None if the point is behind the camera.
if projected is not None:
    cell = projected.coord
    depth = projected.depth  # Distance from the camera. Smaller is nearer.
```

- `distance` is how far the camera is from the origin, and `focal` (the same as `distance` unless you set it)
  controls the scaling.
- `near` clips points closer than that to the camera. Crossing faces and edges keep their visible portions;
  texture coordinates are interpolated at the clipped corners.
- `orthographic=True` turns the scaling off.
- `view_direction(point)` is the direction from a point toward the camera, which decides which faces turn toward it.

## At cell resolution

- Strong perspective makes near faces large and far faces tiny. Tiny faces become a few cells of noise, so keep
  perspective at 1 or below for small shapes.
- Perspective magnifies whatever comes toward you, including text on a surface. Letters on the near side of a large
  shape can double up (see [Texture mapping](textures.md)). Gentler perspective, such as 0.5, reduces it.
- Orthographic views are good for text: a text plane turning in an orthographic view never grows past the size of the
  input.
- Nothing may come nearer than the camera's `near` distance. With `perspective=2` the camera is only 60 columns away,
  so a body moved to z = 60 disappears.

## Coordinates and mutable settings

World **z** increases toward the viewer. Camera **depth** is `camera.distance - world_z`,
so smaller depth is nearer. `cell_to_world(coord, z=...)` accepts world z; `Projected.depth`
and `Mount.depth` report camera depth. Both are measured in columns.

Camera settings are mutable. Construction checks positive `distance`, `focal` (when set), `near`
and `row_scale`, and requires `near < distance`. Assignments do not revalidate: preserve those
constraints when changing a field. With `focal=None`, focal length follows the current distance.
