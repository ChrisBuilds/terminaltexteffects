# Depth and Hidden Surfaces

In a 3D scene, nearer things hide farther ones. The space has to decide, cell by cell, which surface wins. It uses two
tools: a **depth buffer** for surfaces, and **layers** for characters.

## The idea

**Depth** is a point's distance from the camera. Smaller is nearer.

A **depth buffer** keeps, for every cell, the nearest surface found there so far. Each face is filled cell by cell,
and a cell only takes the new face if it's nearer than what the cell already holds. Draw every shape into the same
buffer and overlaps sort themselves out, even where two shapes pass through each other.

![Side view: a ray from the camera through each cell stops at the first surface it meets, so the near surface hides part of the far one](../../img/effectguide/3d/depth_buffer.webp)

**Back-face culling** skips work before the buffer sees it. Each face of a closed shape has an outward **normal**, an
arrow pointing straight out of it. A face whose normal points away from the camera is on the far side of the shape,
hidden behind the near side, so it can be skipped without testing a single cell.

![Seen from above, a turning prism: faces whose normals point toward the camera are drawn, the others are skipped](../../img/effectguide/3d/back_faces.webp)

Mounted characters aren't drawn into the buffer. Each one is a single character on one cell, so the space orders them
with **layers** instead: with `layer_by_depth` on, a nearer character gets a higher layer and draws on top.

## In TTE

The Depth example passes a sphere through a cube, or shows a cube's far side through its text. Save it as
`depth.py`:

```python title="depth.py"
--8<-- "docs/effectguide/examples/3d/depth/depth.py"
```

=== "Overlap"

    ```bash
    tte --input-file concept_input.txt --canvas-width 80 --canvas-height 24 --anchor-text c depth
    ```

    ![A sphere passes through a turning cube; each hides the other where it is nearer](../../img/effectguide/depth_demo.webp)

=== "See-through"

    ```bash
    tte --input-file concept_input.txt --canvas-width 80 --canvas-height 24 --anchor-text c depth --see-through
    ```

    ![A cube covered in text, with its dim far side showing through the spaces](../../img/effectguide/depth_see_through_demo.webp)

- Every drawn body in a space shares one depth buffer, so bodies hide each other correctly with no extra work.
- `Textured(back="dim")` draws a second pass of the faces turned away, in `back_color`, and lets them show through the
  spaces in the text. It's the one place the space draws back faces on purpose.

The Card example mounts the input text on a plane and turns it once, which shows what happens to characters as they
turn edge-on. Save it as `card.py`:

```python title="card.py"
--8<-- "docs/effectguide/examples/3d/card/card.py"
```

=== "Both sides"

    ```bash
    tte --input-file concept_input.txt --canvas-width 80 --canvas-height 24 --anchor-text c card
    ```

    ![The text turns like a card, thinning to a sliver edge-on and showing mirrored on the back](../../img/effectguide/card_demo.webp)

=== "Front only"

    ```bash
    tte --input-file concept_input.txt --canvas-width 80 --canvas-height 24 --anchor-text c card --hide-back
    ```

    ![The same turn, with characters hidden while the back faces the viewer](../../img/effectguide/card_hide_back_demo.webp)

As the card turns edge-on, its columns crowd into fewer cells and only one character can show in each. Past edge-on
you see the back of the card, so the text reads mirrored. `hide_when_facing_away=True` hides each character while its
side faces away, as a solid card would.

## Under the hood

[`geometry3d.rasterize`](../../engine/utils/geometry3d.md) fills a mesh into a buffer and returns it:

```python
from terminaltexteffects.utils import geometry3d as g3

buffer: dict = {}
g3.rasterize(cube_mesh, camera, rotation=turn, buffer=buffer)
g3.rasterize(sphere_mesh, camera, position=g3.Vec3(10, 0, 0), buffer=buffer)
for cell, fragment in buffer.items():
    ...  # fragment.depth, fragment.normal, fragment.facing, fragment.tag, fragment.uv
```

- `cull="back"`, the default, skips faces turned away. `"front"` keeps only those, and `"none"` keeps both.
- Each `Fragment` holds the nearest surface's depth, normal, face tag and texture coordinates.

Characters are ordered by layer, then by creation order. A mount with `layer_by_depth` sets the character's layer to
its layer when mounted plus how much nearer than the origin it is, in whole columns, and restores it on release. The
rest of a column orders characters within the layer, so the nearer of two characters always draws on top, however
small the difference. Surface cells are ordered the same way and count a hair farther than they are, so text mounted
on a drawn body from layer 0 or above reads on top.

## At cell resolution

- Text edge-on loses characters: a plane turned 60 degrees shows only half of its columns. Keep text near facing the
  viewer when it must be read, and move through edge-on quickly.
- Where two characters land in the same cell, the higher layer wins. With `layer_by_depth` off, the last-created
  character wins instead, which looks random on a turning body.
- Only cell centers are tested, so a part of a shape thinner than a cell, such as a narrow rim seen edge-on, can
  fall between centers and vanish for a frame.

## Mounted anchors at the near plane

`mount.projected` reports whether the anchor can be projected at its current pose. While the
anchor is closer than `camera.near` (including behind the camera), its character is automatically
hidden on its tick. The mount retains its last valid coordinate, depth, facing, and light readings;
check `projected` before using them. It restores visibility when the anchor returns, unless
backface hiding still applies. A character already hidden by the effect stays hidden. Releasing
a mount restores visibility only if the mount hid it.
