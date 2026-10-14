# Step 7: Harden

MySpray works on the tutorial text with its default options. A shared effect also meets input you didn't plan for:
colored text, a single character, wide characters, a canvas much larger than the text. In this step MySpray learns to
keep the input's colors, gets tests that run it on unusual input, and is compared with the built-in Spray.

**Engine chapters used:** [Color](../engine/color.md#colors-in-the-input),
[Discovery and loading](../engine/loading.md).

## Update the module

Replace `myspray.py` with this version:

```python title="myspray.py" hl_lines="12 122 143-153"
--8<-- "docs/effectguide/examples/myspray_step7/myspray.py"
```

## What changed

When the user passes `--existing-color-handling dynamic`, the engine leaves input colors to the effect. MySpray now
checks for that setting and, when it is set, gives each character a droplet scene with a single frame in the
character's input colors, instead of the fade into the final gradient. The frame lasts 160 ticks, as long as the
gradient scene, so the effect's timing doesn't change.

A character without input colors gets a `ColorPair` of two `None` colors, so it is shown in the terminal's default
colors. This matches the built-in Spray; Paint, in the Color chapter, falls back to its gradient instead. Either
choice is reasonable, as long as your effect's documentation says which it makes.

The other two settings need no code. With `ignore`, the default, the engine drops the input colors. With `always`, the
engine replaces the colors of every frame with the input colors.

## Run it

Use the colored input file from the [Color](../engine/color.md#colors-in-the-input) chapter:

```bash
tte --input-file color_input.txt --existing-color-handling dynamic myspray
```

The first word lands in its input colors, red, green, and blue, and the second word, which has no colors, lands in
the terminal's default color:

![MySpray with dynamic color handling: the first word keeps its red, green, and blue input colors](../../img/effectguide/myspray_step7_demo.webp)

## Test it

Testing an effect means running it on input that is likely to break it and checking that it finishes with the text
in place. Save this file as `test_myspray.py` outside your community effects directory, since TTE imports every `.py`
file in that directory:

```python title="test_myspray.py"
--8<-- "docs/effectguide/examples/myspray_tests/test_myspray.py"
```

The tests use MySpray from Python, as described in [Configuration from
Python](../engine/configuration.md#configuration-from-python). `play()` sets the frame rate to 0 so the tests don't
wait between frames, and sets `ignore_terminal_dimensions` so the effect runs without a terminal.

- `test_ends_with_the_input_text` runs inputs that often expose bugs: one character, one row, one column, a sparse
  grid with empty lines, wide characters that take two cells, and tabs. It checks that the last frame contains every
  line of the input.
- `test_empty_input_is_rejected_by_the_engine` shows that your effect never sees input without visible characters: the
  engine raises `EmptyInputError` first, and the CLI exits without playing anything.
- `test_every_spray_position_on_a_larger_canvas` runs every spray position on a canvas larger than the text, where
  canvas and text bounds differ.
- `test_dynamic_color_handling_keeps_input_colors` checks that the input's red reaches the last frame.

Run the tests with your effects directory on the import path, so `import myspray` finds the module:

```bash
PYTHONPATH="${XDG_CONFIG_HOME:-$HOME/.config}/terminaltexteffects/effects" python -m pytest test_myspray.py
```

All 17 tests pass. Test anything your own effect adds the same way: each option at its limits, and any input your
effect treats specially.

## Compare with Spray

MySpray now has the same options, defaults, and behavior as the built-in Spray. Here is Spray on the same input:

```bash
tte --input-file color_input.txt --existing-color-handling dynamic spray
```

![The built-in Spray with dynamic color handling, landing the same way as MySpray](../../img/effectguide/spray_colors_demo.webp)

Read [`effect_spray.py`](https://github.com/ChrisBuilds/terminaltexteffects/blob/main/terminaltexteffects/effects/effect_spray.py)
next to your `myspray.py`. The differences are in structure, not behavior:

- Spray converts `--spray-position` to a `SprayPosition` enum and keys its origins by the enum. MySpray keys
  `spray_origin_map` by the option's strings.
- Spray computes every character's final color first and stores it in `character_final_color_map`. MySpray looks the
  color up as it builds each scene.
- With dynamic color handling, Spray's scene has seven 20-tick frames in the input colors, 140 ticks in all, and
  MySpray's has one 160-tick frame. Both show the input colors until the scene ends.
- Spray's docstrings list every option in an `Attributes:` section, and its epilog includes the shared description of
  easing functions, `argutils.EASING_EPILOG`, as built-in effects do.

## What you built

Over seven steps, MySpray went from an effect that printed the text in place to a full copy of Spray. Along the way
it used every major part of the engine: character visibility and release, paths with easing, events, scenes and
gradients, command-line options, and input colors.

From here, the [Patterns](../writing/patterns/phases.md) pages show techniques Spray doesn't use, such as multi-phase effects and particles, and
[Sharing your effect](../writing/sharing.md) explains how to publish yours.
