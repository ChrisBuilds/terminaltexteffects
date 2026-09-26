# Waves

![Demo](../img/effects_demos/waves_demo.gif)

## Quick Start

``` py title="waves.py"
from terminaltexteffects.effects.effect_waves import Waves

effect = Waves("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

## Circular Waves

The default direction, `circle_center_to_outside`, spreads waves outward in circular rings. Use
`circle_outside_to_center` for waves that converge on the text center. These directions account for
terminal character proportions. The existing `center_to_outside` and `outside_to_center` directions
use diamond-shaped groups.

```sh
tte waves --wave-direction circle_center_to_outside
tte waves --wave-direction circle_outside_to_center
```

::: terminaltexteffects.effects.effect_waves
