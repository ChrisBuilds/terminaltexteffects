# Spin, step 1: A sheet of text

This tutorial builds a 3D effect from scratch: Spin. The text starts far behind the canvas as a flat sheet, turned at
a random angle. It comes forward while spinning, unwinds its tilt as it goes, and lands exactly on the input text.
Each character brightens as it turns to face you. This is the finished effect:

```bash
tte --input-file concept_input.txt --canvas-width 80 --canvas-height 24 --anchor-text c spin
```

![The finished Spin effect: the text tumbles in from far away and settles into place](../../../img/effectguide/spin_goal_demo.webp)

!!! info "Spin is in development"

    Spin lives in the repository's `dev_effects/` directory until it is released. To run it from a checkout, add
    `TTE_DEV_EFFECTS_DIR=dev_effects` before `tte`.

Your copy is called **MySpin** and runs as `tte myspin`. It uses the same input and canvas as the
[3D Effects](../index.md#running-the-examples) chapters. If you haven't written an effect before, the
[MySpray tutorial](../../tutorial/01-scaffold.md) covers the parts every effect has, which this one skips over.

In this step you mount the text on a sheet, turn the sheet away, and turn it back.

**3D chapters used:** [Space and coordinates](../coordinates.md), [Transforms](../transforms.md),
[Rotation](../rotation.md).

## Create the module

Save this as `myspin.py` in your community effects directory:

```python title="myspin.py"
--8<-- "docs/effectguide/examples/3d/myspin_step1/myspin.py"
```

## How it works

### The space and the sheet

`Space3D(self.terminal, perspective=0)` sets up a camera looking at the canvas. Perspective 0 is a flat view, so
nothing grows or shrinks with distance yet. Step 3 turns it on.

`self.space.body()` makes a body with no shape. A body is a position, a rotation and a scale. It owns no characters
and draws nothing; it only carries the characters you mount on it.

### Mounting the text

`text_plane(characters)` returns one **anchor** per character: a point on the body, placed so that it lands on the
character's input cell while the body is at rest. `add_chars` mounts each character on its anchor. From then on,
`space.step()` works out where each anchor is on screen, and `update()` moves the character there.

Spaces are left out. They're invisible, so mounting them would only cost time.

### Turning away and back

`set_rotation(rotation_about("y", 70))` turns the sheet 70 degrees about the vertical axis, right away. Because the
anchors were placed first, they turn with the sheet. `turn_to_rest(frames=120, ease=easing.out_cubic)` queues a
**tween** that turns it back to rest along the shortest path, slowing as it arrives.

### Handing the text back

`on_complete(self.finish)` calls `finish` when the sheet's last tween ends. `release_all()` gives the characters back,
on their input cells, as ordinary 2D characters. Once they have nothing left to do, `update()` drops them from
`active_characters` and the effect ends.

## Run it

```bash
tte --input-file concept_input.txt --canvas-width 80 --canvas-height 24 --anchor-text c myspin
```

![MySpin after step 1: the text widens as the sheet turns back to face the viewer](../../../img/effectguide/myspin_step1_demo.webp)

With no perspective, turning the sheet only squeezes the text from the sides. Characters that land on the same
cell hide each other, which is why letters go missing while it's turned.

## Next step

Step 2 replaces the single turn with a spin.
