# Animating in 3D

A 3D effect is still a frame-by-frame effect. Bodies and the camera move a little every frame, either because your
code moves them or because they're playing **tweens** and **paths**. This chapter covers how they're timed, what a
character can read about how it is seen, and how to hand the text back to the ordinary 2D engine once the 3D part is
over.

## The idea

A body's pose has three parts, and each has its own way to animate:

| Part | Step by step | Over frames |
| --- | --- | --- |
| Rotation | `body.rotate("y", 5)`, `body.rotation = ...` | Tweens: `spin`, `settle`, `turn_to`, `turn_to_rest`, `random_pose` |
| Scale | `body.scale = 2.0` | Tween: `scale_to` |
| Position | `body.position = ...` | A path: `body.motion.new_path(...)`, as for characters |

- **Step by step**: your `__next__` changes the body directly. You're in full control, frame by frame. Use this when
  the motion depends on something else in the effect.
- **Over frames**: you describe a change once, such as "two turns about y over 120 frames, easing out", and the world
  plays it a frame at a time inside `update()`. Use this for motion you can describe up front.

Tweens **queue**. Each one starts when the one before it finishes, so a body's queue is its script. A tween queued
with `together=True` joins the one before it and runs at the same time. A body's path runs alongside its tween queue,
independently.

![A timeline: hold for 30 frames, then a y spin and an x spin together for 120 frames, then a settle for 90 frames, with on_complete at the end](../../img/effectguide/3d/tween_timeline.webp)

Tweens add their change to the body rather than setting it, so step-by-step calls and tweens combine. A spin keeps
turning a body that your code is also nudging. Spins running together combine in the order you queued them, so whole
turns that end together finish at the starting pose (see [Tumbling](rotation.md#tumbling)).

Each tween and path has a length and an optional **easing** function, the same ones paths always use (see
[Motion](../engine/motion.md#easing)). Easing changes how the motion is spread over its frames, not how long it takes.

## In TTE

The Handoff example flings the text plane far away, brings it back with a spin that settles exactly at rest, and then
gives every character an ordinary 2D hop. The 3D part is a few lines:

```python
self.plane.rotation = rotation_about("x", 60) * rotation_about("y", 200)
self.plane.position = Vec3(0, 0, -300)
back = self.plane.motion.new_path(speed=300 / 150, ease=easing.out_cubic)
back.new_waypoint(Vec3(0, 0, 0))
self.plane.motion.activate_path(back)
self.plane.settle("y", turns=1, frames=150, ease=easing.out_cubic)
self.plane.on_complete(self.hand_off)  # hand_off starts the hops.
```

??? example "handoff.py"

    Save it in your community effects directory as `handoff.py`.

    ```python
    --8<-- "docs/effectguide/examples/3d/handoff/handoff.py"
    ```

```bash
tte --input-file concept_input.txt --canvas-width 80 --canvas-height 24 --anchor-text c handoff
```

![The text flies in from far away while turning, lands flat, then hops column by column](../../img/effectguide/handoff_demo.webp)

- Setting `rotation` and `position` places the body at its starting pose at once.
- A path's speed is units per frame, so a 300-unit trip at `300 / 150` takes 150 frames, as long as the settle. The
  path and the tween run side by side, so the text turns as it flies in, and both end at rest at the origin.
- `on_complete(callback)` runs when the last queued tween finishes, after every body has moved that frame. The example
  puts the plane exactly at rest with `reset()` there and starts the hops.
- The characters never left the text plane. Once it is back at rest, each one is in its input cell, and an ordinary
  2D path from there just works.

Other tweens: `turn_to(rotation)`, `turn_to_rest()`, `scale_to(scale)`, `hold(frames)` and `random_pose()` for
scattered starts. `body.animating` tracks one body's tweens; `camera.animating` tracks the camera's;
`world.animating` is true while any of them has a tween queued or any body is on a path. None of them knows about
characters' own paths, so end the effect on `active_characters` too (see [the frame loop](index.md#the-text-in-3d)).

## What a character sees

`character.view` reports how a character is seen this frame. Readings are worked out after the world steps, from the
character's place in the world, the camera and the light, so they work for any character on any body:

| Reading | What it is |
| --- | --- |
| `cell` | The cell the character projects to |
| `depth` | Distance along the current view axis, in units: smaller is nearer. Body or camera motion can change it |
| `nearness` | 1 at the nearest point its parent body can reach at its size, 0 at the farthest, measured from the body's center. Moving the body doesn't change it; turning the body or the camera changes which side is nearer |
| `facing`, `facing_amount` | Whether the surface where it sits faces the camera, and how squarely, from -1 (away) to 1 |
| `light` | How directly that surface faces the light, from 0 to 1 |
| `face` | The face of its parent's surface it is on, as `surface.face()` takes it, or `None` |
| `projected` | Whether it is in front of the near plane; the other readings keep their last values while it isn't |

A character free in the world, on a pivot or on the screen has no surface under it, so it counts as facing the camera
in full light.

Scenes can follow two readings with no code in `__next__`: `sync=Scene.SyncMetric.LIGHT` picks the frame from `light`,
and `sync=Scene.SyncMetric.DEPTH` from `nearness`, so the near side of a turning body can show a brighter color than
the far side. For anything else, read the view yourself. This thins out characters as they turn edge-on:

```python
def __next__(self) -> str:
    for character in self.letters:
        symbol = "·" if character.view.facing_amount < 0.3 else character.input_symbol
        character.animation.set_appearance_if_changed(symbol)
    self.update()
    return self.frame
```

Readings in `__next__` before `update()` describe the previous frame, which is what the characters are about to tick
from. Readings in a tween's or path's callback describe the current frame, with every body already moved.

## Handing the text back

Text that stayed on the text plane is home as soon as the text plane and camera are back at their starting pose.
Text that left it needs attaching back, and a path home (see [Coming home](attaching.md#coming-home)):

```python
for character in self.letters:
    character.attach(self.world.text_plane)  # Where it is: no jump.
    home = character.motion.new_path(speed=0.8, ease=easing.in_out_cubic)
    home.new_waypoint(character.input_coord)
    character.motion.activate_path(home)
    self.active_characters.add(character)
```

After the hand-off, the characters are ordinary characters. Their scenes, colors and layers are what you left them
as, so reset anything the 3D part changed.

## Lifecycle

- `body.cancel()` discards queued tweens and their callbacks, and keeps the current pose. `body.reset()` cancels too,
  and restores the pose the body was made with. Both allow new tweens afterwards.
- `body.erase()` stops drawing a body and keeps it in the world.
- `world.remove(body)` takes a body out: it stops its tweens and path, stops drawing it, and detaches its children
  where they are. Removing it again is harmless; a removed body can't be moved or attached to.
- `world.camera.cancel()` stops the camera's tweens, and `world.camera.reset()` cuts back to its starting view.

## Waiting for a group

`on_complete(callback)` belongs to the last individual tween. Use `body.on_group_complete(callback)` to wait for the
longest tween in the last queued parallel group. Both run after the camera and every body have moved that frame, so
they read final poses. Groups queued after the hook are independent; cancelling or resetting discards pending hooks.

## Camera shots and timing

The camera owns its own queue. A camera group and a body group begin independently; `together=True` groups actions on
the **same owner**, not across the camera and a body. Two actions on the camera that start together capture the same
starting pose before either applies a frame. In particular, a simultaneous pan does not alter the forward axis captured
by `dolly_by`.

![Independent camera and body timelines, different pan/truck durations, individual and group completion, and the per-frame phase order](../../img/effectguide/3d/camera_timing.webp)

This shot gives the body a 120-frame turn, while the camera waits, trucks for 90 frames and pans for 45 of them, then
zooms. `on_complete` belongs to the last individual tween, so the pan's callback fires while the truck is still
moving. `on_group_complete` waits for both. Both callbacks receive the camera and return `None`:

```python
--8<-- "docs/effectguide/examples/3d/cameralab/cameralab.py:sequence"
```

```bash
tte --input-file concept_input.txt --canvas-width 80 --canvas-height 32 --anchor-text c cameralab --lesson sequence
```

![A body turns while the camera plays a queued shot; captions mark pan completion, group completion and the independent queue states](../../img/effectguide/camera_sequence_demo.webp)

In each frame, `update()` steps the world first: camera tweens, then each body's tweens and path, then the callbacks of
everything that finished, camera first. Then every character whose place changed is projected again, the active
characters tick, and the drawn bodies are painted. A completion callback can therefore read final readings, or start
the hand-off at the final view.

### Immediate calls, zero frames and deltas

`set_position`, `move_by`, `dolly`, `set_rotation` and `zoom` apply now. Pan, tilt, roll, truck, pedestal, `look_at`
and `orbit` also apply now when `frames` is omitted. Supplying `frames=0` makes them queued zero-frame actions: they
wait behind earlier groups rather than jumping ahead. Negative frame counts raise `ValueError`.

Camera tweens apply **changes** rather than overwrite the pose. For example, after a move tween has begun, an immediate
`move_by(y=2)` adds an offset that the remaining tween preserves. Local travel captures its direction at the start;
turns continue to compose with immediate turns; zoom changes multiply, so an immediate `zoom(2)` doubles the remaining
zoom trajectory. With concurrent edits, the final pose includes those edits and may differ from the original absolute
target.

### Tracking a moving body

[Immediate target movement](camera-movement.md#a-sampled-target-and-a-moving-target) is simple: move the body, then
call `camera.look_at(body)`. A body that moves by tween or path moves inside `update()`, after camera tweens, so aiming
in `__next__` sees where it was last frame. To follow the current frame's position, aim from a one-frame camera hook,
whose callback runs after every body has moved:

```python
from terminaltexteffects.engine.camera import Camera


# A method on the effect iterator:
def aim_after_motion(self, camera: Camera) -> None:
    camera.look_at(self.target)


# In __next__, while the target is moving:
self.world.camera.hold(1).on_complete(self.aim_after_motion)
self.update()
```

Keep the camera queue free for those one-frame hooks; if a shot is already queued, the hook waits behind it. For a
fixed sampled aim, use one `look_at(body, frames=...)` instead.

## Returning the view

`camera.cancel()` clears its tweens and pending callbacks but holds the current view. `camera.reset()` also restores the
camera's starting settings: position, orientation, focal length, projection, center, near plane and row scale, keeping
any perspective set with `set_perspective`. Reset is immediate; it does not accept `frames`. Neither resets bodies.

The text plane's characters land on their input cells only under the starting view. For an eased camera return, capture
its readouts before changing it, then tween position, orientation and focal length together:

```python
# Before changing the camera:
home_position = camera.position
home_rotation = camera.rotation
home_focal = camera.focal or camera.distance

# When returning, after other shot edits are finished:
camera.move_to(home_position, frames=90)
camera.turn_to(home_rotation, frames=90, together=True)
camera.zoom_to(home_focal, frames=90, together=True)
camera.on_group_complete(self.hand_off)  # The text is flat again.
```

If projection, row scale, optical center or near plane were also changed, restore those settings explicitly, or use
`reset()` when a cut is appropriate.

```bash
tte --input-file concept_input.txt --canvas-width 80 --canvas-height 32 --anchor-text c cameralab --lesson restore
```

![The text plane stays still while the camera moves; cancel holds the view, reset cuts home, and a grouped eased return lands the text](../../img/effectguide/camera_restore_demo.webp)

The camera lab captures its starting view in `setup_restore` and leaves the text plane where it is. Its complete return
script is:

```python
--8<-- "docs/effectguide/examples/3d/cameralab/cameralab.py:restore"
```

## Under the hood

A tween is a function of progress from 0 to 1. Each frame, the world advances the front of the camera's queue and
each body's queue by one frame, eases the progress, and applies the change since the last frame. That's why tweens
compose: each applies a difference, not an absolute pose. `settle` and `turn_to` use `Rotation.slerp` to find the
orientation at each step.

## At cell resolution

- Easing matters more in cells than in pixels. A linear spin starts and stops with a visible jolt, and an eased one
  doesn't. The Eases example gives three cubes the same quarter turns with different easing functions:

    ```bash
    tte --input-file concept_input.txt --canvas-width 80 --canvas-height 24 --anchor-text c eases
    ```

    ![Three cubes make the same quarter turns: linear starts and stops abruptly, in_out_sine speeds up and slows down, and out_back overshoots and springs back](../../img/effectguide/eases_demo.webp)

    `turn_to`, `turn_to_rest`, `settle` and `scale_to` take the same `ease` argument as paths. The example's source
    is `docs/effectguide/examples/3d/eases/eases.py` in a TTE checkout.
- Hold a moment at rest before handing text back, so the reader sees it land.
