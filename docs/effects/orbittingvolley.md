# OrbittingVolley

![Demo](../img/effects_demos/orbittingvolley_demo.gif)

## Quick Start

``` py title="orbittingvolley.py"
from terminaltexteffects.effects.effect_orbittingvolley import OrbittingVolley

effect = OrbittingVolley("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_orbittingvolley
