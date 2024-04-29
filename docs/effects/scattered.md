# Scattered

![Demo](../img/effects_demos/scattered_demo.gif)

## Quick Start

``` py title="scattered.py"
from terminaltexteffects.effects.effect_scattered import Scattered

effect = Scattered("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_scattered
