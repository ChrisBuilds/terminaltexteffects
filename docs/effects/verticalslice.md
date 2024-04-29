# VerticalSlice

![Demo](../img/effects_demos/verticalslice_demo.gif)

## Quick Start

``` py title="verticalslice.py"
from terminaltexteffects.effects.effect_verticalslice import VerticalSlice

effect = VerticalSlice("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_verticalslice
