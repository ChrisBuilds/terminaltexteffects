# LaserEtch

![Demo](../img/effects_demos/laseretch_demo.gif)

## Quick Start

``` py title="laseretch.py"
from terminaltexteffects import Gradient
from terminaltexteffects.effects.effect_laseretch import LaserEtch

effect = LaserEtch("YourTextHere")

with effect.terminal_output() as terminal:
    effect.effect_config.final_gradient_direction = Gradient.Direction.HORIZONTAL
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_laseretch
