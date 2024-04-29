# Unstable

![Demo](../img/effects_demos/unstable_demo.gif)

## Quick Start

``` py title="unstable.py"
from terminaltexteffects.effects.effect_unstable import Unstable

effect = Unstable("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_unstable
