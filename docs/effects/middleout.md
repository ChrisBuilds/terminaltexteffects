# MiddleOut

![Demo](../img/effects_demos/middleout_demo.gif)

## Quick Start

``` py title="middleout.py"
from terminaltexteffects.effects.effect_middleout import MiddleOut

effect = MiddleOut("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_middleout
