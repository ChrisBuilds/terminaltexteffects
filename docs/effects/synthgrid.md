# SynthGrid

![Demo](../img/effects_demos/synthgrid_demo.gif)

## Quick Start

``` py title="synthgrid.py"
from terminaltexteffects.effects.effect_synthgrid import SynthGrid

effect = SynthGrid("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_synthgrid
