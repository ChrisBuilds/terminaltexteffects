# Smoke

![Demo](../img/effects_demos/smoke_demo.gif)

## Quick Start

``` py title="smoke.py"
from terminaltexteffects.effects import Smoke

effect = Smoke("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_smoke