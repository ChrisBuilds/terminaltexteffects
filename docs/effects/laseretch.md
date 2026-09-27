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

`--etch-pattern` accepts `algorithm`, every `CharacterGroup`, and every `CharacterSort`.
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

For library use, assign a native enum or its CLI spelling:

```python
from terminaltexteffects.effects.effect_laseretch import LaserEtch
from terminaltexteffects.utils.argutils import CharacterSort

effect = LaserEtch("YourTextHere")
effect.effect_config.etch_pattern = CharacterSort.SPIRAL_CLOCKWISE_QUAD
```

::: terminaltexteffects.effects.effect_laseretch
