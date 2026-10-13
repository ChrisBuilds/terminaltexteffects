# LaserEtch

![Demo](../img/effects_demos/laseretch_demo.gif)

## Quick Start

``` py title="laseretch.py"
from terminaltexteffects import Gradient
from terminaltexteffects.effects.effect_laseretch import LaserEtch

effect = LaserEtch("YourTextHere")
effect.effect_config.final_gradient_direction = Gradient.Direction.HORIZONTAL
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
```

## Etch Patterns

!!! info "New in 0.16.0"

    `CharacterOrder` patterns and `--reverse-etch-pattern` are available on development `main` and are not in
    the published 0.15.0 package.

`--etch-pattern` accepts `algorithm` and every `CharacterOrder`.
The default `algorithm` follows a recursive backtracker. Group patterns reverse alternate groups
for serpentine traversal; sort patterns follow the exact order returned by `Terminal.get_characters()`.

See [Spiral Sorting](../engine/terminal/terminal.md#spiral-sorting) for the six spiral orders, their starting
corners, and how multiple arms interleave.

The laser moves to each
scheduled character; `etch_speed` controls how many characters are etched per emission and
`etch_delay` controls the frames between emissions. Uncolored spaces retain the existing skip behavior.

```bash
tte laseretch --etch-pattern spiral_clockwise
tte laseretch --etch-pattern spiral_counter_clockwise_double --etch-speed 1
```

Use `--reverse-etch-pattern` to reverse the complete traversal while preserving group membership.
The flag defaults to off. Reversed spirals travel outward along the selected path; changing
clockwise to counterclockwise instead selects a different inward path.
Reversal applies after serpentine traversal or after the default algorithm has built its path.

```bash
tte laseretch --etch-pattern spiral_clockwise --reverse-etch-pattern
```

Configurations normalize to `CharacterOrder`. Existing `CharacterGroup` and `CharacterSort`
values and their CLI spellings remain accepted as compatibility inputs.

For library use, assign a native enum or its CLI spelling:

```python
from terminaltexteffects.effects.effect_laseretch import LaserEtch
from terminaltexteffects import CharacterOrder

effect = LaserEtch("YourTextHere")
effect.effect_config.etch_pattern = CharacterOrder.SPIRAL_CLOCKWISE_QUAD
```

::: terminaltexteffects.effects.effect_laseretch
