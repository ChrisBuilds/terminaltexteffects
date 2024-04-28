# Binarypath

![Demo](../img/effects_demos/binarypath_demo.gif)

## Quick Start

``` py title="binarypath.py"
from terminaltexteffects.effects.effect_binarypath import BinaryPath

effect = BinaryPath("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_binarypath
