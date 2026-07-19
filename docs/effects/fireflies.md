# Fireflies

Fireflies drift in from the canvas edges, blink independently, gather around hidden character positions, and gradually illuminate the original text.

## Quick Start

``` py title="fireflies.py"
from terminaltexteffects.effects.effect_fireflies import Fireflies

effect = Fireflies("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

The effect uses input characters as its primary fireflies, so their original symbols, coordinates, and final colors are restored exactly. On tiny canvases, orbiting and atmospheric helpers are reduced while blinking and illumination remain active.

::: terminaltexteffects.effects.effect_fireflies
