# Configuration and the CLI

An effect's options are declared once, as fields of its configuration dataclass. From that one declaration TTE builds
the `tte <effect>` command-line options, their help text and validation, and the defaults used when the effect runs
from Python. This chapter explains how a field is declared and how its value reaches your iterator.

## The configuration class

A configuration class is a dataclass that subclasses [`BaseConfig`](../../engine/baseconfig.md):

```python
@dataclass
class GlowConfig(BaseConfig):
    """Configuration for the Glow effect."""

    parser_spec = argutils.ParserSpec(
        name="glow",
        help="Characters slide home, heating from a red spark to white text.",
        description="glow | Characters slide home, heating from a red spark to white text.",
        epilog="Example: tte glow --sync distance",
    )
    frame_duration: int = argutils.ArgSpec(
        name="--frame-duration",
        type=argutils.PositiveInt.type_parser,
        default=3,
        metavar=argutils.PositiveInt.METAVAR,
        help="Ticks to show each frame of the scene. Ignored when the scene is synced.",
    )  # pyright: ignore[reportAssignmentType]
    "int : Ticks to show each frame of the scene. Ignored when the scene is synced."
```

`parser_spec` describes the subcommand. Its fields are passed to argparse:

| Field | Shown |
| --- | --- |
| `name` | The command, as in `tte glow`. It must match the name `get_effect_resources()` returns. |
| `help` | The one-line summary in the effect list of `tte -h`. |
| `description` | The heading of `tte glow -h`. Built-in effects use `"<name> \| <summary>"`. |
| `epilog` | The text at the end of `tte glow -h`, usually an example command. |

Every other field is an option. Its default value is an [`ArgSpec`](../../engine/utils/argutils.md), and its type
annotation is the type of the value your iterator receives.

The `# pyright: ignore[reportAssignmentType]` comment is needed because the field is annotated as `int` but assigned
an `ArgSpec`; `BaseConfig` replaces the `ArgSpec` with its default when the configuration is created. The string after
the field is its documentation. Built-in effects write it as `"<type> : <help>"` so it appears in the generated
Reference pages.

## Declaring an option

`ArgSpec` takes the arguments of argparse's `add_argument()`:

| Argument | Use |
| --- | --- |
| `name` | The option, such as `"--frame-duration"`. The field name must be the option name in snake case, `frame_duration`, because argparse stores the value under that name. |
| `default` | The value used when the option isn't given. It must already be in its final form, such as `Color("#ffffff")` rather than `"ffffff"`. |
| `type` | A function that turns the command-line string into the value and rejects invalid input. See [Validators](#validators). |
| `metavar` | The placeholder for the value in help, such as `(int > 0)`. Each validator provides one as `METAVAR`. |
| `help` | The option's description. The default is appended automatically, as `(default: 3)`. |
| `choices` | A list of allowed values. Help shows them instead of a metavar. |
| `action` | `"store_true"` for an on/off flag, or `argutils.TupleAction` for an option that takes several values. |
| `nargs` | With `TupleAction`, `"+"` for one or more values. |

A few common shapes:

=== "Choice"

    ```python
    sync: typing.Literal["none", "distance", "step"] = argutils.ArgSpec(
        name="--sync",
        default="none",
        choices=["none", "distance", "step"],
        help="Sync the scene to the character's path.",
    )  # pyright: ignore[reportAssignmentType]
    ```

    The value is the chosen string. Map it to what your effect needs in the iterator, as Glow does with its
    `SYNC_METRICS` dictionary.

=== "Flag"

    ```python
    curve: bool = argutils.ArgSpec(
        name="--curve",
        default=False,
        action="store_true",
        help="Start in the bottom left corner and curve home through the bottom right corner.",
    )  # pyright: ignore[reportAssignmentType]
    ```

    The value is `True` when the option is given. This is Travel's option from the [Motion](motion.md#curves) chapter.

=== "Several values"

    ```python
    final_gradient_steps: tuple[int, ...] = argutils.ArgSpec(
        name="--final-gradient-steps",
        type=argutils.PositiveInt.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=(12,),
        metavar=argutils.PositiveInt.METAVAR,
        help="Number of steps between each pair of final gradient stops.",
    )  # pyright: ignore[reportAssignmentType]
    ```

    `TupleAction` stores the values as a tuple. `type` checks each value separately.

### Validators

[`argutils`](../../engine/utils/argutils.md) has a validator class for each common kind of value. Pass its
`type_parser` as `type` and its `METAVAR` as `metavar`:

| Class | Accepts | Value |
| --- | --- | --- |
| `PositiveInt`, `NonNegativeInt` | `5` | `int` above 0, or 0 and above |
| `PositiveFloat`, `NonNegativeFloat` | `0.5` | `float` above 0, or 0 and above |
| `PositiveRatio`, `NonNegativeRatio` | `0.25` | `float` above 0, or 0 and above, and at most 1 |
| `PositiveIntRange`, `PositiveFloatRange` | `2-8`, `0.6-1.4` | `tuple` of two numbers |
| `ColorArg` | `ff8000`, `208` | `Color` |
| `GradientDirection` | `radial` | `Gradient.Direction` |
| `Ease` | `out_expo` | an easing function |
| `Symbol` | `*` | a one-character `str` |
| `CharacterOrderArg` | `row_top_to_bottom` | `CharacterOrder` |

A validator raises `argparse.ArgumentTypeError` for bad input, and argparse prints the message and exits:

```text
tte myspray: error: argument --spray-volume: invalid value: '2' must be 0 < n <=1. Example: 0.5
```

To write your own, pass any function that takes the command-line string and returns the value, raising
`argparse.ArgumentTypeError` when the string isn't valid. The same function also checks values set from Python, so it
must accept a value that is already in its final form, too: `PositiveInt.type_parser` accepts both `"5"` and `5`.

### The shared final gradient options

Most built-in effects end with the text in a gradient, and they share three option declarations from
[`terminaltexteffects.engine.base_config`](../../engine/baseconfig.md): `FinalGradientStopsArg`, `FinalGradientStepsArg`,
and `FinalGradientDirectionArg`. Each is an `ArgSpec` with the name, validator, and help already filled in. Pass a
`default` to change only the default:

```python
final_gradient_stops: tuple[Color, ...] = FinalGradientStopsArg(
    default=(Color("#8A008A"), Color("#00D1FF"), Color("#FFFFFF")),
)  # pyright: ignore[reportAssignmentType]
```

Using them gives your effect the same `--final-gradient-*` options users know from the built-in effects.

## Reading the configuration

The iterator receives the configuration as `self.config`, with every option already converted and validated. The
user's terminal options, such as `--existing-color-handling` and `--frame-rate`, are in `self.terminal.config`.

```python
spray_origin = spray_origin_map[self.config.spray_position]
dynamic = self.terminal.config.existing_color_handling == "dynamic"
```

Read options as you build the effect. Don't change them from the iterator.

## Configuration from Python

An effect can also run from Python, without the CLI. The configuration is then created with the `ArgSpec` defaults,
and the caller can change any field before iterating:

```python
effect = MySpray(text)
effect.effect_config.spray_position = "center"
effect.effect_config.movement_speed_range = "0.2-0.5"  # Converted to (0.2, 0.5).
```

Assigning a field runs it through the same `type` and `choices` checks as the CLI, so it converts command-line
spellings and raises `ValueError` for invalid values. This is why the `type` function must accept values in their final
form as well as strings. The [Library Guide](../../libguide.md) covers running effects from Python.

## Shell completion

The completion scripts that `tte --print-completion` prints are bundled with TTE and list only the built-in effects.
They don't complete the commands or options of community effects.

## Where to go next

- [Tutorial step 6: Configure](../tutorial/06-configure.md) turns MySpray's fixed values into options.
- The [`argutils` Reference](../../engine/utils/argutils.md) lists every validator.
