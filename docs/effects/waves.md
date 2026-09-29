# Waves

![Demo](../img/effects_demos/waves_demo.gif)

## Quick Start

``` py title="waves.py"
from terminaltexteffects.effects.effect_waves import Waves

effect = Waves("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

## Circular Waves

The default direction, `circle_center_to_outside`, spreads waves outward in circular rings. Use
`circle_outside_to_center` for waves that converge on the text center. These directions account for
terminal character proportions. The existing `diamonds_center_to_outside` and `diamonds_outside_to_center` directions
use diamond-shaped groups. The former `center_to_outside` and `outside_to_center` spellings remain
accepted as compatibility aliases.

```sh
tte waves --wave-direction circle_center_to_outside
tte waves --wave-direction circle_outside_to_center
```

## Character Orders and Reversal

`--wave-direction` accepts every `CharacterOrder`: rows, columns, diagonals, diamond and circular
bands, individual row traversals, random order, and all six spiral patterns. Spatial orders activate
one complete group per frame. Individual orders activate one character per frame, so they can take
longer on dense text. Double and quad spiral arms interleave in that individual character sequence.
The default remains `circle_center_to_outside`.

Use `--reverse-wave-direction` to reverse activation order while retaining each group's membership.
Reversed spirals travel outward along the selected path. Reversal defaults to off.

```sh
tte waves --wave-direction spiral_clockwise_quad
tte waves --wave-direction spiral_counter_clockwise_double --reverse-wave-direction
```

```python
from terminaltexteffects import CharacterOrder
from terminaltexteffects.effects.effect_waves import Waves

effect = Waves("YourTextHere")
effect.effect_config.wave_direction = CharacterOrder.SPIRAL_CLOCKWISE
effect.effect_config.reverse_wave_direction = True
```

CLI names, including the previous eight directions, and legacy `CharacterGroup` / `CharacterSort`
values normalize to `CharacterOrder`. The circular default and grouped activation timing are unchanged.

::: terminaltexteffects.effects.effect_waves
