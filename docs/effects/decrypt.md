# Decrypt

![Demo](../img/effects_demos/decrypt_demo.gif)

## Quick Start

``` py title="decrypt.py"
from terminaltexteffects.effects.effect_decrypt import Decrypt

effect = Decrypt("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_decrypt
