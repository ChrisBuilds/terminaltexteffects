# Wipe

![Demo](../img/effects_demos/wipe_demo.gif)

## Quick Start

``` py title="wipe.py"
from terminaltexteffects.effects.effect_wipe import Wipe

effect = Wipe("YourTextHere")
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

## Wipe Directions and Sorts

`--wipe-direction` accepts every `CharacterOrder`. Group directions reveal whole
rows, columns, diagonals, or radial bands. Sort directions reveal individual characters in the exact
order returned by `Terminal.get_characters()`, using their input coordinates.

The spiral sorts wind inward from the input's bounds:

| Clockwise | Counterclockwise | Starting corners |
| --- | --- | --- |
| `spiral_clockwise` | `spiral_counter_clockwise` | Top-left |
| `spiral_clockwise_double` | `spiral_counter_clockwise_double` | Top-left and bottom-right |
| `spiral_clockwise_quad` | `spiral_counter_clockwise_quad` | All four corners |

Double and quad spirals interleave their arms in the character sequence. Both grouped and sorted
modes use the same 100-step easing schedule, so multiple characters may appear in one frame.
`wipe_delay` adds frames before the first easing step and between later steps. Easing functions that
reverse temporarily hide characters and restart their wipe scenes when those characters reappear.
The default remains `diagonal_top_left_to_bottom_right`.

```sh
tte wipe --wipe-direction spiral_clockwise
tte wipe --wipe-direction spiral_counter_clockwise_double --wipe-delay 2
```

Use `--reverse-wipe-direction` to reverse the complete traversal while preserving group membership.
The flag defaults to off. Reversed spirals travel outward along the selected path; changing
clockwise to counterclockwise instead selects a different inward path.

```sh
tte wipe --wipe-direction spiral_clockwise --reverse-wipe-direction
```

Configurations normalize to `CharacterOrder`. Existing `CharacterGroup` and `CharacterSort`
values and their CLI spellings remain accepted as compatibility inputs.

For library use, assign a native enum or its CLI spelling:

```python
from terminaltexteffects.effects.effect_wipe import Wipe
from terminaltexteffects import CharacterOrder

effect = Wipe("YourTextHere")
effect.effect_config.wipe_direction = CharacterOrder.SPIRAL_CLOCKWISE_QUAD
```

::: terminaltexteffects.effects.effect_wipe
