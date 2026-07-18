# Elephant Splash

![Demo](../img/effects_demos/elephantsplash_demo.gif)

A purple elephant walks along the canvas floor to a small puddle, lowers its trunk as the water disappears, then
sprays the water upward to reveal the centred input. After an ear-wiggle celebration, it walks off along the bottom.

## Quick Start

``` py title="elephantsplash.py"
from terminaltexteffects.effects.effect_elephant_splash import ElephantSplash

effect = ElephantSplash("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

For the full elephant choreography, use a canvas of at least 24 columns by 10 rows. A taller canvas gives the clearest
separation between the floor-level elephant and centred branding. Smaller canvases automatically use a compact
elephant or a particle-free splash reveal.

::: terminaltexteffects.effects.effect_elephant_splash
