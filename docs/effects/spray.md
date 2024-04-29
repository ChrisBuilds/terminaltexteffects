# Spray

![Demo](../img/effects_demos/spray_demo.gif)

## Quick Start

``` py title="spray.py"
from terminaltexteffects.effects.effect_spray import Spray

effect = Spray("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_spray
