# Animating in 3D

A 3D effect is still a frame-by-frame effect. Bodies move a little every frame, either because your code moves them
or because they're playing **tweens**. This chapter covers both, how tweens are timed, and how to hand the text back
to the ordinary 2D engine once the 3D part is over.

## The idea

There are two ways to animate a body, and they work together:

- **Step by step**: your `__next__` changes the body directly, with `rotate`, `move_by`, `set_rotation` and the rest.
  You're in full control, frame by frame. Use this when the motion depends on something else in the effect.
- **Tweens**: you describe a change once, such as "two turns about y over 120 frames, easing out", and the space
  plays it a frame at a time. Use this for motion you can describe up front.

Tweens **queue**. Each one starts when the one before it finishes, so a body's queue is its script. A tween queued with
`together=True` joins the one before it and runs at the same time.

![A timeline: hold for 30 frames, then a y spin and an x spin together for 120 frames, then a settle for 90 frames, with on_complete at the end](../../img/effectguide/3d/tween_timeline.webp)

Tweens add their change to the body rather than setting it, so step-by-step calls and tweens combine. A spin keeps
turning a body that your code is also nudging.

Each tween has a length in frames and an optional **easing** function, the same ones paths use (see
[Motion](../engine/motion.md#easing)). Easing changes how the motion is spread over its frames, not how long it
takes.

## In TTE

The Handoff example flings the text plane far away, brings it back with a spin that settles exactly at rest, and then
releases every character to an ordinary 2D hop. Save it as `handoff.py`:

```python title="handoff.py"
--8<-- "docs/effectguide/examples/3d/handoff/handoff.py"
```

```bash
tte --input-file concept_input.txt --canvas-width 80 --canvas-height 24 --anchor-text c handoff
```

![The text flies in from far away while turning, lands flat, then hops column by column](../../img/effectguide/handoff_demo.webp)

- `set_rotation(...)` and `set_position(...)` place the body at its starting pose at once. `move_to(..., frames=0)`
  would do the same as a tween.
- `move_to` and `settle(..., together=True)` run together, so the text turns as it flies in, and lands at rest, where
  every character meets its input cell.
- `on_complete(callback)` runs when the last queued tween finishes, after the final pose is applied. The example
  releases the characters there.
- `release_all()` hands each character back on the cell its anchor reached, with nothing left of the mount, so a new path starts from
  exactly that cell.

Other tweens: `turn_to(rotation)`, `turn_to_rest()`, `scale_to(scale)`, `hold(frames)`, and `random_pose()` and
`random_position()` for scattered starts. `body.animating` and `space.animating` tell you whether anything is still
queued.

### Mounting mid-effect

Mounting and paths are both part of a character's `Motion`, so they hand off cleanly in both directions:

- `space.mount(character, anchor, blend_frames=30, ease=...)` lets a character travel to its anchor from wherever it is,
  instead of jumping.
- Activating a path releases the mount, and mounting deactivates the path.
- The `MOUNT_COMPLETE` and `MOUNT_RELEASED` events, and the `MOUNT` and `UNMOUNT` actions, chain mounts with paths and
  scenes through the [event handler](../engine/events.md). `space.new_mount()` creates a mount for the `MOUNT` action
  without starting it.

## Lifecycle

`body.cancel()` discards queued tweens and completion callbacks while keeping the current pose.
`reset()` also restores the starting pose. Both allow new tweens afterwards.

Use `space.remove(body)` to stop tracking a body: it cancels tweens, releases mounts, and hides
surface cells immediately. Repeated removal is harmless; a body from another space is rejected.
Removed bodies are no longer drawn or stepped and their anchors cannot be mounted again.
Create a new body to add geometry back. `space.clear()` removes all current bodies.
The space retains its surface-character pool for reuse; `erase()` alone only stops surface drawing.


## Under the hood

A tween is a function of progress from 0 to 1. Each frame, `step()` advances the front of each body's queue by one
frame, eases the progress, and applies the change since the last frame. That's why tweens compose: each applies a
difference, not an absolute pose. `settle` and `turn_to` use `Rotation.slerp` to find the orientation at each step.

## At cell resolution

- Easing matters more in cells than in pixels. A linear spin starts and stops with a visible jolt, and an eased one
  doesn't. The Eases example gives three cubes the same quarter turns with different easing functions:

    ```bash
    tte --input-file concept_input.txt --canvas-width 80 --canvas-height 24 --anchor-text c eases
    ```

    ![Three cubes make the same quarter turns: linear starts and stops abruptly, in_out_sine speeds up and slows down, and out_back overshoots and springs back](../../img/effectguide/eases_demo.webp)

    `turn_to`, `turn_to_rest`, `settle`, `move_to` and `scale_to` take the same `ease` argument. The example's source
    is `docs/effectguide/examples/3d/eases/eases.py` in a TTE checkout.
- Hold a moment at rest before releasing text, so the reader sees it land.
- After the hand-off, characters are ordinary characters. Their scenes, colors and layers are what you left them as,
  so reset anything the 3D part changed.

## Waiting for a group or a blend

`on_complete(callback)` belongs to the last individual tween. Use
`body.on_group_complete(callback)` to wait for the longest tween in the last queued parallel group.
The hook runs after mount readings refresh, so it can release mounted characters at the final pose.
Groups queued after the hook are independent; cancelling or resetting discards pending hooks.

`space.animating` tracks body tweens. Mount travel is separate: use `space.blending` to wait for
active blends, or `mount.blend_progress` for the fraction of blend frames elapsed before easing.
Blends advance when characters tick, and a zero-frame blend reports 1 immediately.
