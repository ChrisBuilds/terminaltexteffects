# Elephant Splash

![Demo](../img/effects_demos/elephantsplash_demo.gif)

## Quick Start

``` py title="elephantsplash.py"
from terminaltexteffects.effects.effect_elephant_splash import ElephantSplash

effect = ElephantSplash("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

For the full elephant choreography, use a canvas of at least 24 columns by 10 rows. Smaller canvases automatically
use a compact elephant or a particle-free splash reveal.

::: terminaltexteffects.effects.effect_elephant_splash
