# Elephant Splash

![Demo](../img/effects_demos/elephantsplash_demo.gif)

A large purple elephant walks along the canvas floor to a rippling puddle, lowers its trunk as bubbles draw the water
upward, then sprays it toward the centred input. After an ear-wiggle celebration, it walks off along the bottom.

## Quick Start

``` py title="elephantsplash.py"
from terminaltexteffects.effects.effect_elephant_splash import ElephantSplash

effect = ElephantSplash("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

For the full elephant choreography, use a canvas of at least 41 columns by 16 rows. A taller canvas gives the clearest
separation between the floor-level elephant and centred branding. Smaller canvases automatically use a compact
elephant or a particle-free splash reveal.

The full-size elephant artwork is adapted from an ASCII elephant by `jgs`, published at
[asciiart.website](https://asciiart.website/art/4937). The on-screen signature is omitted to keep the animation clean.

::: terminaltexteffects.effects.effect_elephant_splash
