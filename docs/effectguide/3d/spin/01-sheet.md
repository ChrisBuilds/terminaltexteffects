# Spin, step 1: A sheet of text

This tutorial builds a 3D effect from scratch: Spin. The text starts far behind the canvas as a flat sheet, turned at
a random angle. It comes forward while spinning, unwinds its tilt as it goes, and lands exactly on the input text.
Each character brightens as it turns to face you. This is what you'll have at the end:

![The finished effect: the text tumbles in from far away and settles into place](../../../img/effectguide/myspin_step6_demo.webp)

Your copy is called **MySpin** and runs as `tte myspin`. It uses the same input and canvas as the
[3D Effects](../index.md#running-the-examples) chapters. If you haven't written an effect before, the
[MySpray tutorial](../../tutorial/01-scaffold.md) covers the parts every effect has, which this one skips over.

In this step you turn the text away on its sheet, the text plane, and turn it back.

**3D chapters used:** [The world](../world.md), [Frames and coordinates](../coordinates.md),
[Rotation](../rotation.md).

## Create the module

Save this as `myspin.py` in your community effects directory:

```python title="myspin.py"
--8<-- "docs/effectguide/examples/3d/myspin_step1/myspin.py"
```

## How it works

### The world and the sheet

Every terminal has a world, `self.terminal.world`, with a camera looking at the canvas.
`world.camera.set_perspective(0)` makes the view flat, so nothing grows or shrinks with distance yet. Step 3 turns
perspective on.

The sheet is `world.text_plane`, the body every character starts on. Each character's position is its input cell on
the text plane's surface, and those positions never change in this tutorial: the effect moves the plane, and the
plane carries the text. The text is in its input cells whenever the plane is at rest.

### Showing the text

`build` makes each character visible and adds it to `active_characters`, so it is drawn from the first frame.
Characters in this step have nothing of their own to do, so `update()` drops them from `active_characters` after the
first tick. They still move: whenever the view changes, the world projects every character on the plane again.
Step 4 gives each character a scene, which does need a tick every frame.

Spaces are left out. They're invisible, so showing them would only cost time.

### Turning away and back

`rotate("y", 70)` turns the sheet 70 degrees about the vertical axis, right away.
`turn_to_rest(frames=120, ease=easing.out_cubic)` queues a **tween** that turns it back to rest along the shortest
path, slowing as it arrives. The world plays the tween one frame at a time inside `update()`.

### Ending

`__next__` keeps going while `self.world.animating` or `self.active_characters` is true. `animating` is true while
any body or camera tween is queued or playing, so the effect ends on the frame after the sheet comes to rest, with the
text in its input cells.

## Run it

```bash
tte --input-file concept_input.txt --canvas-width 80 --canvas-height 24 --anchor-text c myspin
```

![MySpin after step 1: the text widens as the sheet turns back to face the viewer](../../../img/effectguide/myspin_step1_demo.webp)

With no perspective, turning the sheet only squeezes the text from the sides. Characters that land on the same
cell hide each other, which is why letters go missing while it's turned.

## Next step

Step 2 replaces the single turn with a spin.
