# Geometry 3D

*Module*: `terminaltexteffects.utils.geometry3d`

!!! info "New in 0.16.0"

    `geometry3d` is available on development `main` and is not in the published 0.15.0 package.

Low-level building blocks for placing and drawing things in 3D on a terminal canvas: vectors, rotations, a
camera, meshes, rasterization into a per-cell depth buffer, wireframe edges and Lambert shading.

World space is measured in terminal columns. The origin is the center of the canvas, +x points right, +y points
up, and +z points toward the viewer. A `Camera` projects world points onto canvas cells and corrects for cells
being about twice as tall as they are wide, so a cube looks like a cube. With the default settings, a cell lifted
onto the z=0 plane with `Camera.cell_to_world()` projects back onto the same cell.

```python
import math

from terminaltexteffects.utils import geometry3d as g3

camera = g3.Camera(center_column=40.5, center_row=12.5)
cube = g3.box(20, 20, 20)
turn = g3.Rotation.about_y(math.radians(30)) * g3.Rotation.about_x(math.radians(20))
light = g3.Vec3(-0.5, 0.6, 1.0)

for cell, fragment in g3.rasterize(cube, camera, rotation=turn).items():
    brightness = g3.lambert(fragment.normal, light)  # 0 in shadow, 1 facing the light
```

Camera position and orientation can change with `set_position` and `set_rotation`. `depth(point)` reports
view-axis depth. `ray(coord)` supplies a world ray, and `cell_to_world(coord, z=...)` intersects it with a world-z
plane, raising `ValueError` for parallel rays. For movement helpers and tweens, use `Space3D.camera`.

Angles are in radians. Rotations compose with `*`: `second * first` applies `first`, then `second`.

`rasterize` and `wireframe` take `bounds=g3.Bounds.for_canvas(canvas)` to fill only cells on the canvas. Without
bounds they fill every cell a shape covers, which can be a great many for a shape close to the camera.

::: terminaltexteffects.utils.geometry3d
