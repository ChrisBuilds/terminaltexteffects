# Step 3: Move

So far, released characters appear in place. In Spray they fly out from a single point on the edge of the canvas and
land in their place in the text. In this step each character gets a path from that point to its home.

**Engine chapters used:** [Canvas and coordinates](../engine/canvas.md), [Motion](../engine/motion.md).

## Update the module

Replace `myspray.py` with this version:

```python title="myspray.py" hl_lines="11 44-66"
--8<-- "docs/effectguide/examples/myspray_step3/myspray.py"
```

## What changed

### The spray origin

`spray_origin_map` names nine positions on the canvas: its center, the middle of each edge, and each corner. They use
canvas bounds rather than text bounds, so the spray starts from the edge of the canvas even when the canvas is larger
than the text. Positions on the right edge use `canvas.right - 1`, one column in from the edge.

MySpray always uses `"e"`, the middle of the right edge, for now. Step 6 turns the position into an option, which is why
all nine are listed already.

### A path for every character

For each character, `build()` now:

1. Moves the character to the spray origin with `set_coordinate()`.
2. Creates a path with a random speed between 0.6 and 1.4 and the `out_expo` easing, so characters leave the origin
   fast and slow down as they arrive.
3. Adds one waypoint, the character's home, `input_coord`.
4. Activates the path. Because the character isn't in `active_characters` yet, it doesn't move until it is released.

The random speeds spread out the arrival times, so the text doesn't land all at once.

`__next__` is unchanged. Releasing a character now adds a character with an unfinished path to `active_characters`, so
it stays active and moves each tick until it reaches home. The effect ends when the last character lands.

## Run it

```bash
tte --input-file tutorial_input.txt myspray
```

Characters stream out from the right edge, spread across the text, and settle into place:

![MySpray after step 3: characters fly from the right edge to their places](../../img/effectguide/myspray_step3_demo.webp)

Moving characters cross characters that have already landed. Every character is on layer 0, so where two overlap, the
one with the higher `character_id` is drawn on top, and a flying character can disappear behind a settled one.

## Next step

Step 4 uses events to put moving characters on a higher layer, so they always pass in front.
