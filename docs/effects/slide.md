# Slide

![Demo](../img/effects_demos/slide_demo.gif)

## Quick Start

``` py title="slide.py"
from terminaltexteffects.effects.effect_slide import Slide

effect = Slide("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_slide
