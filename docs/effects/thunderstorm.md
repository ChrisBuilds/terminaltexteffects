# Thunderstorm

![Demo](../img/effects_demos/thunderstorm_demo.gif)

## Quick Start

``` py title="thunderstorm.py"
from terminaltexteffects.effects import Thunderstorm

effect = Thunderstorm("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_thunderstorm