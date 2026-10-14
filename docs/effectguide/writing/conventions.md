# Conventions and quality

The built-in effects follow shared conventions, so users can guess an option's name and trust that every effect
handles the same inputs. Following them makes your effect feel like part of TTE. This page collects those conventions,
then gives a checklist of inputs to try before you share.

## Options

### Names

- Write option names in lowercase, with words separated by hyphens: `--movement-speed`. The configuration field is the
  same name in snake case, `movement_speed`. It has to be, because argparse stores the value under that name (see
  [Declaring an option](../engine/configuration.md#declaring-an-option)).
- Start with what the option affects and end with what it controls, as in `--spray-position`, `--movement-speed`,
  and `--wipe-delay`. The built-in effects use these endings most:

| Ending | Controls | Examples |
| --- | --- | --- |
| `-speed` | Distance per tick. | `--movement-speed`, `--travel-speed` |
| `-easing` | An easing function. | `--movement-easing`, `--wave-easing` |
| `-color`, `-colors` | One color, or several to choose from. | `--starting-color`, `--rain-colors` |
| `-symbols` | Symbols to choose from. | `--rain-symbols`, `--wave-symbols` |
| `-gradient-stops`, `-gradient-steps`, `-gradient-direction` | A gradient. | `--wave-gradient-stops` |
| `-delay`, `-time`, `-frames` | A number of ticks. | `--launch-delay`, `--final-gradient-frames` |
| `-range` | A pair of values to pick between, written `low-high`. | `--movement-speed-range` |

- Use the shared `--final-gradient-stops`, `--final-gradient-steps`, and `--final-gradient-direction` declarations
  for the gradient the text ends in. Nearly every built-in effect has them (see
  [The shared final gradient options](../engine/configuration.md#the-shared-final-gradient-options)).

### Values and defaults

- Validate every value with a validator from `argutils` or your own `type` function, so bad input fails with a clear
  message instead of an exception from inside the effect.
- Choose defaults that look good on ordinary text in an ordinary terminal. Most users never change them.
- Measure durations in ticks, and say so in the help. At the default 60 frames per second, 60 ticks is one second.
- For a count where `0` means "forever", such as cycles, say so in the help, and keep the default finite (see
  [Looping and infinite effects](patterns/looping.md)).

### Help text

- Give every option a one-sentence `help` ending in a period. The default is added automatically.
- Use the `epilog` for an example command that shows a useful combination of options.
- Write the field's documentation string as `"<type> : <help>"`, as the built-in effects do.

## Code

- Import only public names: the `terminaltexteffects` package exports and the public modules under
  `terminaltexteffects.engine` and `terminaltexteffects.utils`. Names that start with an underscore can change in any
  release.
- Do the effect's setup in the iterator's `__init__()`, or a `build()` method it calls, and keep module-level code to
  definitions, since TTE imports every effect module on every run (see [Discovery and loading](../engine/loading.md)).
- Keep `__next__` to the work for one frame. Anything that can be computed once, such as a gradient mapping, belongs in
  setup.
- Use `random` from the standard library for randomness. `tte --seed` seeds it, which makes runs repeatable for
  recordings and bug reports.
- Write docstrings for the module, the classes, and their methods. Refer to code with single backticks, such as
  `ParticlePool`.

## Input colors

Decide what your effect does with each `--existing-color-handling` setting, and document it:

- With `ignore` and `always`, the engine does the work, so check only that the effect still looks right.
- With `dynamic`, the effect decides. Use `character.animation.input_fg_color` and `input_bg_color` where your effect
  would otherwise apply its own final colors, and choose what happens to characters without input colors.

[Color](../engine/color.md#colors-in-the-input) and [Step 7: Harden](../tutorial/07-harden.md) show both sides.

## Edge-case checklist

Run your effect on each of these before you share it. [Step 7: Harden](../tutorial/07-harden.md#test-it) shows how to
turn them into tests.

| Input or option | What can go wrong |
| --- | --- |
| One character | Divisions by the text width or height, such as gradient mappings or spacing, divide by zero. |
| One row, one column | Effects that pick a random row or column, or need two of them, fail or look wrong. |
| Sparse text with empty lines and leading spaces | Groups or rows are empty, and code that assumes every row has characters fails. |
| Wide characters, such as `漢字` | Code that assumes one character per cell overlaps or misplaces characters. |
| Tabs | Tabs become spaces according to `--tab-width`; the text is wider than its character count. |
| A canvas larger than the text, `--canvas-width 0 --canvas-height 0` | Code that mixes up canvas bounds and text bounds places things in the wrong area. |
| Text larger than the terminal | Characters outside the visible area are clipped; check that the effect still ends. |
| Colored input with each `--existing-color-handling` setting | Colors are lost, or `dynamic` ignores characters without input colors. |
| `--no-color` and `--xterm-colors` | The effect depends on color to be readable. |
| `--frame-rate 0` | The effect relies on time passing between frames instead of counting ticks. |
| Every value of every choice option, and the limits of every numeric option | A rarely used value fails. |

Input with no visible characters never reaches your effect: the engine rejects it first.

## Where to go next

- [Sharing your effect](sharing.md) covers what to publish with the effect.
- [Performance](../engine/performance.md) covers keeping frames fast on large input.
