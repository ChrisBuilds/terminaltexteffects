# Waves

![Demo](../img/effects_demos/waves_demo.gif)

## Quick Start

``` py title="waves.py"
from terminaltexteffects.effects.effect_waves import Waves

effect = Waves("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_waves
