# OrbittingVolley

Four launchers travel along the canvas edges, firing characters from the side nearest their final position.
The text builds in expanding circular rings around its center, adjusted for terminal cell height.
Every character in a ring launches before the next ring opens. Up to two rings can have characters
still in flight; a third waits for one of them to finish arriving. Launchers with no characters assigned
in the current ring keep moving while the other launchers fire. The effect finishes after all characters arrive.

The default `launch_delay` is `1`, leaving one animation tick between volleys. Increase it for longer pauses.

![Demo](../img/effects_demos/orbittingvolley_demo.gif)

## Quick Start

``` py title="orbittingvolley.py"
from terminaltexteffects.effects.effect_orbittingvolley import OrbittingVolley

effect = OrbittingVolley("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_orbittingvolley
