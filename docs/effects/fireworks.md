# Fireworks

![Demo](../img/effects_demos/fireworks_demo.gif)

## Quick Start

``` py title="fireworks.py"
from terminaltexteffects.effects.effect_fireworks import Fireworks

effect = Fireworks("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_fireworks
