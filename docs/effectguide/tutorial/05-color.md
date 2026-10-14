# Step 5: Color

So far every character has been drawn in the terminal's default color. In Spray, the text ends in a gradient that runs
from purple at the bottom, through cyan, to white at the top, and each character fades into its color from a random
color of that gradient while it flies. In this step each character gets a scene that does this.

**Engine chapters used:** [Animation](../engine/animation.md), [Color](../engine/color.md).

## Update the module

Replace `myspray.py` with this version:

```python title="myspray.py" hl_lines="11 46-53 85-92"
--8<-- "docs/effectguide/examples/myspray_step5/myspray.py"
```

## What changed

### The final gradient

`build()` starts by creating the final gradient, from purple through cyan to white with 12 steps between each pair of
stops. `build_coordinate_color_mapping()` then gives every coordinate in the text a color from it. With
`Gradient.Direction.VERTICAL`, every character in a row gets the same color, from the first stop on the bottom row to
the last stop on the top row.

The mapping uses the text bounds, not the canvas bounds, so the gradient spans the text even when the canvas is larger.

### A droplet scene for every character

For each character, `build()` also:

1. Creates a scene with `new_scene()`.
2. Builds a short gradient from a random color in the final gradient to the character's own color, with 7 steps, so
   8 colors.
3. Adds a frame for each of those colors with `apply_gradient_to_symbols()`. Every frame shows the input symbol and
   lasts 20 ticks, so the scene lasts 160 ticks.
4. Activates the scene.

The random starting colors make the flying characters a mix of the gradient's colors, and each one settles to its
place in the gradient.

The scene isn't synced to the path, so it plays at its own pace. Every path here takes under 100 ticks, so each
character lands before its scene ends and keeps fading in place. A character stays active until both its path and its
scene are complete, so the effect now ends when the last character finishes fading rather than when it lands.

## Run it

```bash
tte --input-file tutorial_input.txt myspray
```

The characters fly in colored and fade to the final gradient, purple at the bottom and white at the top:

![MySpray after step 5: colored characters fly in and fade into a vertical gradient](../../img/effectguide/myspray_step5_demo.webp)

MySpray now looks like the built-in Spray effect with its default options.

## Next step

Step 6 adds command-line options for the spray position, speed, colors, and more, in place of the values written into
the code.
