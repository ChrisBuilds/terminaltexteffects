# Rotation

Turning is what makes 3D look like 3D, and it's the part with the most surprises. This chapter covers turning about
one axis, combining turns into a tumble, and the two ways to bring a body back to rest.

## The idea

A turn has an **axis** and an **angle**. The axis is a line through the body's origin. A positive angle turns
counterclockwise when you look down the axis toward the origin:

- About **y** (up), the body turns like a revolving door.
- About **x** (right), it tips forward or back. A positive angle tips the top toward the default viewer, so you see it from above in that view.
- About **z** (toward the default viewer), it turns like a clock hand, counterclockwise.

![Three cubes turning about x, y and z, each with its axis drawn through it](../../img/effectguide/3d/rotation_axes.webp)

Turns don't add up like numbers. Turning a cube -90 degrees about x, which carries its front face up onto the top,
and then 90 degrees about y leaves it facing a different way than making the same two turns in the other order.

![A cube turned -90 degrees about x then 90 about y ends with its amber front face on top; turned 90 about y then -90 about x, the amber face ends on the right](../../img/effectguide/3d/rotation_order.webp)

So TTE never stores an orientation as three angles, which would depend on the order you applied them in. It stores
a **quaternion**: four numbers that describe the whole orientation as one turn about one axis. You never need to read them. What matters is what they make
easy: combining turns, turning by part of a turn, and finding the shortest way from one orientation to another.

## In TTE

The Turns example has three modes. In the first, each cube spins about one axis:

```python
for axis, x in (("x", -26), ("y", 0), ("z", 26)):
    cube = self.world.body(Cube(14), at=(x, 0, 0)).draw(Shaded())
    cube.hold(30).spin(axis, turns=1, frames=240, ease=easing.in_out_sine).hold(30)
```

??? example "turns.py"

    Save it in your community effects directory as `turns.py`.

    ```python
    --8<-- "docs/effectguide/examples/3d/turns/turns.py"
    ```

### One axis at a time

```bash
tte --input-file concept_input.txt --canvas-width 80 --canvas-height 24 --anchor-text c turns
```

![Three cubes, labeled about x, about y and about z, each turn about that axis](../../img/effectguide/turns_axes_demo.webp)

`spin(axis, turns, frames, ease)` queues whole or partial turns about an axis. It's a **tween**: the world plays it
one frame at a time inside `update()`. `rotate(axis, degrees)` turns the body by that much right away instead, which is
useful when your own code decides the angle each frame.

Both turn about the **parent's** axes by default, which for a body in the world are the world's axes.
`rotate("y", 5)` on a body you've already tipped forward turns it about the screen's vertical. Use `rotate("y", 5, local=True)` or
`spin("y", local=True)` to turn about the body's own tipped axis. The local axis follows the body
when other turns run alongside it (see [Tumbling](#tumbling) for the order spins together combine in).

![Two tilted boxes turn. Left, spin("y") turns about world y, and the box's own axis sweeps a cone. Right, spin("y", local=True) turns about the box's own axis, which stays put](../../img/effectguide/3d/rotation_local.webp)

`settle` still spins about a parent axis while returning to rest. `turn_to` and `turn_to_rest`
target an absolute orientation, so they have no local-axis option.

### Tumbling

```bash
tte --input-file concept_input.txt --canvas-width 80 --canvas-height 24 --anchor-text c turns --mode tumble
```

![A cube spins about y and x at once](../../img/effectguide/turns_tumble_demo.webp)

`together=True` runs a tween alongside the one queued before it. Two spins about different axes running together
combine into a tumble.

Spins that run together combine from each spin's angle so far. On every frame the pose is the group's starting pose,
turned once per spin in the order you queued them, just as `rotate(axis, angle)` calls would turn it, or
`rotate(axis, angle, local=True)` for a local spin. A parent axis stays fixed in the parent. A local axis is the body's
own, carried by the spins queued before it. Whole turns that end together therefore bring the body back to the pose it
started from:

```python
plane.spin("x", turns=1, frames=120)
plane.spin("y", turns=1, frames=120, together=True)  # After 120 frames the plane is back where it started.
```

Each spin keeps its own length and easing. One that finishes early holds its final angle until the others finish.
Changes you make between frames, such as `rotate`, turn the pose the spins carry, as they would for a single spin.
`cancel()` stops every spin where it is.

A tween with a target, `turn_to`, `turn_to_rest`, `random_pose` or `settle`, sets the pose the spins in its group turn.
On every frame the body is at the tween's own pose for that frame, turned by the spins as above, so the spins carry it
along its path. Whole turns that end with or before the tween therefore land it exactly on its target:

```python
plane.turn_to(rotation_about("x", 90), frames=60)
plane.spin("y", turns=1, frames=60, together=True)  # After 60 frames the plane is at rotation_about("x", 90).
```

A partial turn also turns the target. With `turns=0.5` above, the plane ends at `rotation_about("y", 180)` times
`rotation_about("x", 90)`, as if it had reached the target and then made the half turn.

### Back to rest

```bash
tte --input-file concept_input.txt --canvas-width 80 --canvas-height 24 --anchor-text c turns --mode rest
```

![Two cubes start in the same pose. The left one, labeled turn_to_rest, turns straight back to rest. The right one, labeled settle, spins as it settles](../../img/effectguide/turns_rest_demo.webp)

**Rest** is the orientation a body was created in, with no turn applied. It matters most for the text plane: its
characters are in their input cells whenever it is at rest, at the origin and at scale 1. The Spin tutorial turns the
text plane away and back, so returning to rest brings the text home. Rest is only an orientation: if you also moved
or scaled the body, bring its position and scale back too, with a path and `scale_to`, or all at once with `reset()`
(see [Frames and coordinates](coordinates.md#rest-and-pose)).

There are two ways back to rest:

- `turn_to_rest(frames, ease)` takes the shortest path. It looks like a body being straightened.
- `settle(axis, turns, frames, ease)` spins about an axis while it unwinds any other tilt, landing exactly at rest.
  It looks like a coin or a sign coming to a stop.

`turn_to(rotation)` turns along the shortest path to any orientation, and `random_pose()` turns to a random one,
drawn from Python's `random` module, so `random.seed` makes it repeatable.

## Under the hood

[`geometry3d.Rotation`](../../engine/utils/geometry3d.md) is the quaternion. Its angles are in radians:

```python
import math

from terminaltexteffects.engine.tweens import rotation_about
from terminaltexteffects.utils.geometry3d import Rotation, Vec3

tip = Rotation.about_x(math.radians(20))
turn = rotation_about("y", 45)  # The same, but in degrees and with axis names.
both = tip * turn  # Turn first, then tip.
halfway = Rotation().slerp(both, 0.5)  # Halfway from rest to `both`, along the shortest path.
point = both.apply(Vec3(10, 0, 0))
```

- `a * b` is the rotation that applies `b` first, then `a`.
- `inverse()` undoes a rotation.
- `slerp(other, t)` blends along the shortest path. `turn_to` and `settle` are built on it.
- `matrix()` gives the 3 by 3 matrix that `apply` and `transform_points` use.

## At cell resolution

- A fast turn skips cells. At more than a few degrees per frame, a large shape's edges jump visibly. Ease spins in and
  out, or slow them down.
- In the default view, turns about world z look flat because they move points parallel to the image. Once the
  camera turns, world z need not be the view axis. A [camera roll](camera-movement.md#turn-the-view-without-moving-the-eye)
  always turns about the camera's own backward axis; it is distinct from turning a body about world z.
- Text turned edge-on loses characters (see [Depth and hidden surfaces](depth.md)), so don't leave a text plane
  turned past about 60 degrees for long.
