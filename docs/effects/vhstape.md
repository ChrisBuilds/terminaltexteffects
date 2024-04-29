# VHSTape

![Demo](../img/effects_demos/vhstape_demo.gif)

## Quick Start

``` py title="vhstape.py"
from terminaltexteffects.effects.effect_vhstape import VHSTape

effect = VHSTape("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_vhstape
