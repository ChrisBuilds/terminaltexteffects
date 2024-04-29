# Swarm

![Demo](../img/effects_demos/swarm_demo.gif)

## Quick Start

``` py title="swarm.py"
from terminaltexteffects.effects.effect_swarm import Swarm

effect = Swarm("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_swarm
