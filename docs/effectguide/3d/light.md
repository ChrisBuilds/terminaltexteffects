# Light and Shading

Shading is what makes a filled shape look solid. Without it, a cube is a flat blob of one symbol. With it, each face
gets a symbol and color from how directly it faces the light, and the shape's form reads at once.

## The idea

The space has one **directional** light: a single direction pointing toward it, the same everywhere in the scene,
like sunlight. It has no position, so nothing is nearer to it or farther from it. For each face, the space compares
two arrows: the face's normal and that direction.

- Facing the light squarely, the face is fully lit.
- Turned edge-on to the light, it's unlit.
- In between, brightness falls off smoothly with the angle. The measure is called **Lambert** shading: the cosine of
  the angle between the two arrows, from 1 (facing the light) to 0 (edge-on or facing away).

That number picks a symbol from a ramp and a color from a gradient, both ordered from unlit to fully lit. Unlit faces
still get the first symbol and color, so the shape's dark side stays visible.

Because only the angle counts, there's no falloff with distance and no cast shadows: a face turned toward the light
is lit even if another shape stands between them. Each face is shaded on its own.

![A face turns under a fixed light; as the angle between its normal and the light grows, the brightness bar falls and a dimmer symbol is chosen](../../img/effectguide/3d/lambert.webp)

## In TTE

The Light example moves the light in a circle around a slowly turning shape. A yellow `☼` and a dotted ray mark
the light's direction, and the shape hides them while the light is behind. The light is just a direction, changed
each frame:

```python
angle = 2 * math.pi * self.frame_number / self.frames
self.space.light = Vec3(math.sin(angle), 0.5, math.cos(angle)).normalized()
```

??? example "light.py"

    Save it in your community effects directory as `light.py`.

    ```python
    --8<-- "docs/effectguide/examples/3d/light/light.py"
    ```

=== "Sphere"

    ```bash
    tte --input-file concept_input.txt --canvas-width 80 --canvas-height 24 --anchor-text c light
    ```

    ![A shaded sphere whose bright side follows a sun and its dotted ray circling it](../../img/effectguide/light_demo.webp)

=== "Torus with blocks"

    ```bash
    tte --input-file concept_input.txt --canvas-width 80 --canvas-height 24 --anchor-text c light --shape torus --symbols "░▒▓█"
    ```

    ![A torus shaded with block symbols, its bright side following the sun and its ray](../../img/effectguide/light_torus_demo.webp)

- `Space3D(terminal, light="upper left")` sets the light at creation: `"upper left"`, `"upper right"`, `"front"`,
  `"above"`, `"left"`, `"right"`, or any `(x, y, z)` direction. The default, upper left, gives most shapes a lit
  side, a shadowed side and a top.
- `space.light` is a unit vector you can change each frame, as the example does. The example's sun is only a marker
  placed along that direction so you can see it. Moving the marker wouldn't move the light, and the light doesn't
  shine from the marker's position.
- `Shaded(gradient, symbols)` fills faces from the ramp. The default symbols `.,-~:;=!*#$@` get denser as they get
  brighter. Block symbols such as `░▒▓█` read as solid and suit large shapes.
- `Solid(symbol, gradient)` uses one symbol and lets color alone show the light. It and `Textured` add a little
  **ambient** light, coloring by `0.15 + 0.85 x lambert`, so their unlit faces aren't the darkest color.
- Gradients default to the TTE brand colors, purple to cyan to white.

Mounted characters can follow the light too. Each mount reports `light`, the Lambert value for its anchor's normal,
and a scene created with `sync=Scene.SyncMetric.LIGHT` picks its frame from it. The [logo recipe](recipes.md#spinning-logo)
uses that to brighten text as it turns toward the light. Only anchors with a
[normal](coordinates.md#normals-for-anchors) have a direction to compare: `text_plane` and the shape layouts give
their anchors one, and an anchor made without one always reports `light=1`.

## World light or camera light?

The light direction can live in either of two coordinate spaces:

| Setting | Meaning of `light="front"` | When the camera turns |
| --- | --- | --- |
| `light_space="world"` (default) | Fixed world +z | The same world faces remain lit |
| `light_space="camera"` | Camera-local +z, back toward the eye | The light rotates with the view, like a headlight |

![The camera circles a fixed cube; a world light arrow stays fixed, while the camera-relative arrow turns with the eye](../../img/effectguide/3d/camera_light.webp)

These recordings use the same stationary cube and camera orbit. Only `light_space` changes. The light remains
**directional** in both: camera translation does not cause falloff or turn it into a point light at the eye.

=== "World light"

    ```python
    self.space = Space3D(self.terminal, light="front", light_space="world")
    ```

    ```bash
    tte --input-file concept_input.txt --canvas-width 80 --canvas-height 32 --anchor-text c cameralab --lesson world-light
    ```

    ![As the camera orbits, the cube's world-front face stays bright and its world-back face stays dark](../../img/effectguide/camera_world_light_demo.webp)

=== "Camera light"

    ```python
    self.space = Space3D(self.terminal, light="front", light_space="camera")
    ```

    ```bash
    tte --input-file concept_input.txt --canvas-width 80 --canvas-height 32 --anchor-text c cameralab --lesson camera-light
    ```

    ![As the camera orbits, the headlight keeps the currently viewed faces lit](../../img/effectguide/camera_camera_light_demo.webp)

`space.light` stores the configured direction in the selected coordinate space. Surface shading and mount `light`
readings use the same mode. Body normals remain in world space after the body transform, so a manual Lambert
calculation must convert a camera-relative light into world coordinates first.

## Under the hood

[`geometry3d.lambert(normal, light)`](../../engine/utils/geometry3d.md) returns the Lambert value. With a face's
normal from the depth buffer, choosing a symbol is one line:

```python
from terminaltexteffects.utils import geometry3d as g3

world_light = self.space.light
if self.space.light_space == "camera":
    world_light = self.space.camera.rotation.apply(world_light)
shade = g3.lambert(fragment.normal, world_light)
symbol = ramp[min(len(ramp) - 1, int(shade * len(ramp)))]
color = gradient.get_color_at_fraction(shade)
```

Each face is flat, so all of its cells share one normal and one symbol. That's why a sphere shows bands rather than a
smooth fade, and why more segments make the shading smoother.

## At cell resolution

- Pick ramps where each symbol is clearly denser than the last. Ten or twelve steps is plenty, and fewer can look
  bolder.
- Color carries most of the shading in a dark terminal. A gradient from a dark color to a bright one works with
  almost any symbols.
- A camera-relative `"front"` light points back along the current view axis, so visible faces come out bright and
  the shape can look flat. In an orthographic view, facing that light and facing the viewer agree. In perspective,
  off-axis viewing rays differ a little. A light from one side often shows form better. In world mode, `"front"`
  means fixed world +z and is viewer-facing only while the camera has its default orientation.
