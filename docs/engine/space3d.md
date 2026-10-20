# Space3D

*Module*: `terminaltexteffects.engine.space3d`

!!! info "New in 0.16.0"

    `Space3D` and character mounting are available on development `main` and are not in the published 0.15.0
    package.

`Space3D` lets an effect move its own characters through 3D. It holds a camera centered on the canvas, a light and
any number of bodies. A body is geometry that moves in 3D: a cube, a prism, a sphere, or a plain frame of reference.
Bodies own no characters. The effect mounts its characters on anchors (points on a body) and releases them when it
wants them back. While a character is mounted, only its position comes from 3D, so its scenes, events and layer keep
working as usual.

World units are terminal columns. The origin is the center of the canvas, +x points right, +y points up and +z points
toward the default viewer. World axes stay fixed when the camera turns. Angles are degrees, and axes are `"x"`, `"y"`, `"z"`, `"diagonal"` or any `(x, y, z)` direction.
For the vectors, rotations and projection underneath, see [Geometry 3D](utils/geometry3d.md).

## Moving bodies

An effect can change a body one step at a time from `__next__`. `rotate`, `move_by`, `scale_by` and the `set_*`
methods take effect immediately. It can also queue tweens that `Space3D.step()` plays one frame at a time: `spin`,
`settle`, `turn_to`, `turn_to_rest`, `move_to`, `scale_to`, `random_pose`, `random_position` and `hold`. Each tween
runs after the previous one, or alongside it with `together=True`, and `on_complete` runs a callback when one
finishes. Callbacks run once every body has moved and every mount has been refreshed, so characters released there
are handed over at the final pose. Tweens add their change to the body instead of overwriting it, so a spin keeps turning a body that the
effect is also nudging.

## Moving the camera

`space.camera` is a [`Camera`](#terminaltexteffects.engine.space3d.Camera), extending `geometry3d.Camera` with
immediate movement and a tween queue. It supports dolly, truck, pedestal, pan, tilt, roll, look-at, orbit and zoom.
Camera tweens count toward `space.animating` and advance in `space.step()` before body tweens. Completion callbacks
run after mount readings refresh. See [Moving the camera](../effectguide/3d/camera-movement.md) for the
controls, target sampling, lighting and layout conventions.

## Camera readouts and projection helpers

The high-level `Camera` inherits its settings and projection helpers from `geometry3d.Camera`. They work on
`space.camera` alongside the controls:

| Members | Meaning |
| --- | --- |
| `position`, `rotation` | Read-only world eye and orientation; change them through setters or controls |
| `distance`, `focal` | Legacy initial eye distance / fallback focal, and an optional explicit focal length |
| `orthographic`, `near`, `row_scale` | Projection kind, minimum view-axis depth and tall-cell correction |
| `center_column`, `center_row` | Optical center in canvas cells |
| `project`, `project_points` | World points to projected cells and depths, or `None` before the near plane |
| `depth`, `view_direction` | View-axis depth and direction back toward the viewer |
| `ray`, `cell_to_world` | A world viewing ray, or its intersection with a world-z plane |

Defaults, mutable-setting behavior, orthographic differences and errors are explained in
[Camera and projection](../effectguide/3d/camera.md). `set_position` and `move_to` take absolute coordinates;
`move_by` takes a world displacement; dolly/truck/pedestal use camera-local axes. `look_at` and `orbit` sample body
targets when queued actions begin. Their `frames` argument is optional: omission applies immediately, whereas zero
obeys queue ordering. Other tween methods default to 60 frames.

Camera cancellation drops pending callbacks and keeps the pose. Reset also restores initial projection settings.
`space.clear()` removes bodies; cancel camera work separately if you are ending the whole scene.

## Mounting characters

Anchors move with their body. `body.anchor(x, y, z)` makes one, and layouts make many:

- `text_plane(characters)`: one anchor per character, placed so each sits on its input cell at the body's pose.
- `surface(count)`, `vertices()` and `edges(count)`: spread over a shape.
- `ring(count, radius)`: a circle around the body.
- `wrap(characters)`: text wrapped around a `Cylinder` or `Sphere`.

`space.mount(character, anchor)` hands the character's position to the anchor. The `blend_frames` and `ease` options
make it travel there from wherever it is. Mounting also sets two defaults:

- `layer_by_depth=True` makes nearer characters draw over farther ones.
- `hide_when_facing_away` can hide a character while its side of the body faces away.

`space.release(character)` gives the character back where it stands, ready for a path, and undoes only what the
mount itself changed.

Mounting is part of `Motion`, so it works with the rest of the engine:

- A mounted character counts as active.
- Activating a path releases the mount, and mounting deactivates the path.
- The `MOUNT_COMPLETE` and `MOUNT_RELEASED` events and the `MOUNT` and `UNMOUNT` actions chain mounts with paths
  and scenes. Use `space.new_mount()` to create a mount for the `MOUNT` action.

Each mount reports `depth`, `nearness`, `facing`, `facing_amount` and `light` after every `step()`. An effect can read
these to set its own appearance. A scene created with `sync=Scene.SyncMetric.LIGHT` or `Scene.SyncMetric.DEPTH`
picks its frame from the mount's light or nearness, so 3D shading can be authored as an ordinary gradient scene.

## Drawing surfaces

Mounted characters leave gaps on a solid. To fill every covered cell, draw the body with a look:

- `Shaded(gradient, symbols)` fills faces with a symbol ramp and gradient, picked by each face's angle to the light.
- `Solid(symbol, gradient)` uses one symbol, colored by the light.
- `Textured(text=None, back="hide")` wraps the input text, or any string, over the faces. With `back="dim"` the far
  side shows through the spaces in the text.
- `Wireframe(color, hidden_color)` draws only the edges, with hidden edges dimmed or left out.

Gradients default to the TTE brand colors. `body.draw(look)` starts drawing, `faces={tag: look}` gives faces
their own looks (a die is one argument), and `body.erase()` stops. Each `step()` draws every drawn body into one
depth buffer, so overlapping bodies hide each other correctly.

The space draws surfaces with characters it creates, one per covered cell, and never uses the effect's own
characters. `body.surface_characters` lists the ones showing a body after the last `step()`. An effect can restyle
them, but each `step()` redraws them. Surface cells are ordered by their exact depth, like mounted characters, and
count a hair farther than they are, so text mounted on a drawn body from the default layer 0 or above reads on top
of it.

```python
self.die = self.space.body(Cube(16)).draw(Shaded(), faces={0: Textured("1"), 2: Textured("6")})
self.die.random_pose(frames=90, ease=easing.out_cubic)
```

The following snippet runs inside an effect iterator, where `self.terminal` and `self.active_characters` are
available:

```python
from terminaltexteffects import Color, Gradient, Scene, easing
from terminaltexteffects.engine.space3d import Cube, Space3D

self.space = Space3D(self.terminal)
self.cube = self.space.body(Cube(20))
self.cube.spin("y", turns=2, frames=240, ease=easing.in_out_sine).settle("x", frames=120)  # (1)

characters = [c for c in self.terminal.get_characters() if c.input_symbol != " "]
shade = Gradient(Color("#5a005a"), Color("#00D1FF"), Color("#ffffff"), steps=12)
for character, anchor in zip(characters, self.cube.surface(len(characters))):
    scene = character.animation.new_scene(sync=Scene.SyncMetric.LIGHT)  # (2)
    scene.apply_gradient_to_symbols(character.input_symbol, 1, fg_gradient=shade)
    character.animation.activate_scene(scene)
    self.space.mount(character, anchor, blend_frames=40, hide_when_facing_away=True)
    self.terminal.set_character_visibility(character, is_visible=True)
    self.active_characters.add(character)


def __next__(self) -> str:
    if not self.space.animating:
        raise StopIteration
    self.space.step()  # (3)
    self.update()
    return self.frame
```

1. Two full turns about y, then a turn about x that eases out any tilt and ends at rest.
2. Each frame of this scene is a step along the gradient. The mount's `light` picks the frame, so faces brighten as
   they turn toward the light.
3. Plays the tweens and refreshes every mount's readings. `update()` then ticks the characters, which moves mounted
   characters onto their anchors.

Position arguments accept a `geometry3d.Vec3` or an `(x, y, z)` tuple in terminal columns.
Body/camera placement uses world coordinates; `Body.anchor` and `Body.world_point` take body-local
coordinates. `move_by` takes a relative world displacement. Existing scalar x/y/z calls remain
supported; omit y/z when supplying a complete point and use keywords for animation timing.
See [position input forms](../effectguide/3d/coordinates.md#position-input-forms) for examples.

::: terminaltexteffects.engine.space3d
    options:
      inherited_members:
        - position
        - rotation
        - center_column
        - center_row
        - distance
        - focal
        - orthographic
        - near
        - row_scale
        - project
        - project_points
        - depth
        - view_direction
        - ray
        - cell_to_world
        - for_canvas
