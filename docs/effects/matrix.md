# Matrix

![Demo](../img/effects_demos/matrix_demo.gif)

## Quick Start

``` py title="matrix.py"
from terminaltexteffects.effects.effect_matrix import Matrix

effect = Matrix("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_matrix
