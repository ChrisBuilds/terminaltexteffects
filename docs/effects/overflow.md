# Overflow

![Demo](../img/effects_demos/overflow_demo.gif)

## Quick Start

``` py title="overflow.py"
from terminaltexteffects.effects.effect_overflow import Overflow

effect = Overflow("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_overflow
