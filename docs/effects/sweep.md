# Sweep

![Demo](../img/effects_demos/sweep_demo.gif)

## Quick Start

``` py title="sweep.py"
import terminaltexteffects as tte
from terminaltexteffects.effects.effect_sweep import Sweep

effect = Sweep("YourTextHere")
effect.effect_config.final_gradient_direction = tte.Gradient.Direction.HORIZONTAL
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_sweep
