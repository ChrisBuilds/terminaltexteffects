# Rings

![Demo](../img/effects_demos/rings_demo.gif)

## Quick Start

``` py title="rings.py"
from terminaltexteffects.effects.effect_rings import Rings

effect = Rings("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_rings
