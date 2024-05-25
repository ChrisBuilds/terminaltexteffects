# ColorShift

![Demo](../img/effects_demos/colorshift_demo.gif)

## Quick Start

``` py title="colorshift.py"
from terminaltexteffects.effects.effect_colorshift import ColorShift

effect = ColorShift("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_colorshift
