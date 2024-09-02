# ColorShift

![Demo](../img/effects_demos/colorshift_demo.gif)

## Quick Start

``` py title="colorshift.py"
from terminaltexteffects import Gradient
from terminaltexteffects.effects.effect_colorshift import ColorShift

effect = ColorShift("YourTextHere")
effect.effect_config.travel = True
effect.effect_config.travel_direction = Gradient.Direction.RADIAL
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_colorshift
