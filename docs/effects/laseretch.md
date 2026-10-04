# LaserEtch

![Demo](../img/effects_demos/laseretch_demo.gif)

## Quick Start

``` py title="laseretch.py"
from terminaltexteffects import Gradient
from terminaltexteffects.effects.effect_laseretch import LaserEtch

effect = LaserEtch("YourTextHere")

with effect.terminal_output() as terminal:
    effect.effect_config.final_gradient_direction = Gradient.Direction.HORIZONTAL
    for frame in effect:
        terminal.print(frame)
```

## Etch Patterns

`--etch-pattern` accepts `algorithm` and every `CharacterOrder`.
The default `algorithm` follows a recursive backtracker. Group patterns reverse alternate groups
for serpentine traversal; sort patterns follow the exact order returned by `Terminal.get_characters()`.

The spiral sorts wind inward from the selected input coordinates' bounds:

| Clockwise | Counterclockwise | Starting corners |
| --- | --- | --- |
| `spiral_clockwise` | `spiral_counter_clockwise` | Top-left |
| `spiral_clockwise_double` | `spiral_counter_clockwise_double` | Top-left and bottom-right |
| `spiral_clockwise_quad` | `spiral_counter_clockwise_quad` | All four corners |

Double and quad spiral arms are interleaved in the character sequence. The laser moves to each
scheduled character; `etch_speed` controls how many characters are etched per emission and
`etch_delay` controls the frames between emissions. Uncolored spaces retain the existing skip behavior.

```sh
tte laseretch --etch-pattern spiral_clockwise
tte laseretch --etch-pattern spiral_counter_clockwise_double --etch-speed 1
```

Use `--reverse-etch-pattern` to reverse the complete traversal while preserving group membership.
The flag defaults to off. Reversed spirals travel outward along the selected path; changing
clockwise to counterclockwise instead selects a different inward path.
Reversal applies after serpentine traversal or after the default algorithm has built its path.

```sh
tte laseretch --etch-pattern spiral_clockwise --reverse-etch-pattern
```

Configurations normalize to `CharacterOrder`. Existing `CharacterGroup` and `CharacterSort`
values and their CLI spellings remain accepted as compatibility inputs.

For library use, assign a native enum or its CLI spelling:

```python
from terminaltexteffects.effects.effect_laseretch import LaserEtch
from terminaltexteffects import CharacterOrder

effect = LaserEtch("YourTextHere")
effect.effect_config.etch_pattern = CharacterOrder.SPIRAL_CLOCKWISE_QUAD
```

::: terminaltexteffects.effects.effect_laseretch
