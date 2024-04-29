# Spotlights

![Demo](../img/effects_demos/spotlights_demo.gif)

## Quick Start

``` py title="spotlights.py"
from terminaltexteffects.effects.effect_spotlights import Spotlights

effect = Spotlights("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_spotlights
