# Slice

![Demo](../img/effects_demos/slice_demo.gif)

## Quick Start

``` py title="slice.py"
from terminaltexteffects.effects.effect_slice import Slice

effect = Slice("YourTextHere")
effect.effect_config.slice_direction = "diagonal"
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_slice
