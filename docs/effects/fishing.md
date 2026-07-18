# Fishing

Several fishing lines cast from the top of the canvas, catch scattered swimming characters, and reel them into their
correct final text positions. Hooks briefly tug at each catch, transport it across the canvas, and cleanly disappear
after the text settles. Each hook also has a small, bounded chance to catch harmless junk before retrying its target.

## Quick Start

``` py title="fishing.py"
from terminaltexteffects.effects import Fishing

effect = Fishing("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

::: terminaltexteffects.effects.effect_fishing
