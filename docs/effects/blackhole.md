# Blackhole

![Demo](../img/effects_demos/blackhole_demo.gif)

## Quick Start

``` py title="blackhole.py"
from terminaltexteffects.effects.effect_blackhole import Blackhole

effect = Blackhole("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_blackhole
