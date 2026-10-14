# Step 6: Configure

MySpray now looks like Spray, but every value is fixed in the code: the spray comes from the right edge, the speeds are
between 0.6 and 1.4, and the gradient is always purple to white. In this step those values become command-line options,
with the values used so far as their defaults.

**Engine chapter used:** [Configuration and the CLI](../engine/configuration.md).

## Update the module

Replace `myspray.py` with this version:

```python title="myspray.py" hl_lines="9 13-18 30-88 102 108 121 125-126 153"
--8<-- "docs/effectguide/examples/myspray_step6/myspray.py"
```

## What changed

### The options

`MySprayConfig` now has seven options, the same as the built-in Spray:

| Option | Validator | Default |
| --- | --- | --- |
| `--spray-position` | `choices`, the nine keys of `spray_origin_map` | `e` |
| `--spray-volume` | `PositiveRatio` | `0.005` |
| `--movement-speed-range` | `PositiveFloatRange` | `0.6-1.4` |
| `--movement-easing` | `Ease` | `out_expo` |
| `--final-gradient-stops` | `FinalGradientStopsArg` | `8A008A 00D1FF FFFFFF` |
| `--final-gradient-steps` | `FinalGradientStepsArg` | `12` |
| `--final-gradient-direction` | `FinalGradientDirectionArg` | `vertical` |

The first four are declared with `ArgSpec`. The three final gradient options use the shared declarations from
`terminaltexteffects.engine.base_config`, which already have their names, validators, and help, so MySpray only sets
their defaults. The epilog now shows an example that uses two of the options.

### Using the options

`build()` reads each value from `self.config` where it used a fixed value before. The values are already converted:
`movement_speed_range` is a tuple of two floats, so `random.uniform(*self.config.movement_speed_range)` picks a speed
between them; `movement_easing` is the easing function itself; and `final_gradient_stops` is a tuple of `Color`
objects ready to pass to `Gradient`.

`spray_position` is one of the keys of `spray_origin_map`, the dictionary from step 3, so it selects the origin
directly.

## Run it

With no options, MySpray runs as it did in step 5:

```bash
tte --input-file tutorial_input.txt myspray
```

![MySpray after step 6 with default options: the same as step 5](../../img/effectguide/myspray_step6_demo.webp)

The options change it. This command, the one in the epilog, sprays from the center of the canvas and colors the text
with a radial gradient:

```bash
tte --input-file tutorial_input.txt myspray --spray-position center --final-gradient-direction radial
```

![MySpray spraying from the center into a radial gradient, purple in the middle and white at the corners](../../img/effectguide/myspray_step6_options_demo.webp)

`tte myspray -h` lists the options with their defaults:

```text
--8<-- "docs/effectguide/examples/myspray_step6/help.txt"
```

Invalid values are rejected before the effect starts:

```console
$ tte --input-file tutorial_input.txt myspray --spray-volume 2
tte myspray: error: argument --spray-volume: invalid value: '2' must be 0 < n <=1. Example: 0.5
```

argparse prints the usage lines shown above before the error.

## Next step

Step 7 handles colors in the input, tests MySpray against unusual input, and compares the result with the built-in
Spray.
