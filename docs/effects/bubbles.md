# Bubbles

![Demo](../img/effects_demos/bubbles_demo.gif)

## Quick Start

``` py title="bubbles.py"
from terminaltexteffects.effects.effect_bubbles import Bubbles

effect = Bubbles("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_bubbles
