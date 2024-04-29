# ErrorCorrect

![Demo](../img/effects_demos/errorcorrect_demo.gif)

## Quick Start

``` py title="errorcorrect.py"
from terminaltexteffects.effects.effect_errorcorrect import ErrorCorrect

effect = ErrorCorrect("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_errorcorrect
