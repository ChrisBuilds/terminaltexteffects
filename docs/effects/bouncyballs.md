# BouncyBalls

![Demo](../img/effects_demos/bouncyballs_demo.gif)

## Quick Start

``` py title="bouncyballs.py"
from terminaltexteffects.effects.effect_bouncyballs import BouncyBalls

effect = BouncyBalls("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_bouncyballs
