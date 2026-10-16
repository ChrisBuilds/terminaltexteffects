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
- `on_complete(callback)` runs when the last queued tween finishes. The example releases the characters there.
- `release_all()` hands each character back where it stands, with nothing left of the mount, so a new path starts from
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

## Under the hood

A tween is a function of progress from 0 to 1. Each frame, `step()` advances the front of each body's queue by one
frame, eases the progress, and applies the change since the last frame. That's why tweens compose: each applies a
difference, not an absolute pose. `settle` and `turn_to` use `Rotation.slerp` to find the orientation at each step.

## At cell resolution

- Easing matters more in cells than in pixels. A linear spin starts and stops with a visible jolt, and an eased one
  doesn't.
- Hold a moment at rest before releasing text, so the reader sees it land.
- After the hand-off, characters are ordinary characters. Their scenes, colors and layers are what you left them as,
  so reset anything the 3D part changed.
