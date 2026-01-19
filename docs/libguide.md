# Library Guide

## Playing Effect Animations

All effects are iterators which return a string representing the current frame. Basic usage is as simple as importing
the effect, instantiating it with the input text, and iterating over the effect. Effects includes a helpful context
manager
([effect.terminal_output()](./engine/baseeffect.md#terminaltexteffects.engine.base_effect.BaseEffect.terminal_output))
to handle terminal setup/teardown and cursor positioning.

The following example plays the [Slide](./effects/slide.md) effect animation using the [effect.terminal_output()](./engine/baseeffect.md#terminaltexteffects.engine.base_effect.BaseEffect.terminal_output) context manager.

=== "Syntax"

    ```python
    from terminaltexteffects.effects.effect_slide import Slide

    text = ("EXAMPLE" * 10 + "\n") * 10

    effect = Slide(text)
    effect.effect_config.merge = True # (1)
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
    ```
    
    1. Use the `effect_config` attribute to modify the effect configuration. Setting `merge` to `True` on the Slide effect causes the text to slide
    in from alternating sides of the terminal.

=== "Output"
    ![t](./img/lib_demos/libguide_onlyslide_output.gif)

## Effects are Iterable

If you want to handle the output yourself, such as sending the frames to a TUI or GUI, simply iterate over the effect without the context manager.

```python
from terminaltexteffects.effects.effect_slide import Slide

text = ("EXAMPLE" * 10 + "\n") * 10

effect = Slide(text)
effect.effect_config.merge = True # (1)
for frame in effect:
    # frame is a string, do something with it
```

1. Use the `effect_config` attribute to modify the effect configuration. Setting `merge` to `True` on the Slide effect causes the text to slide
in from alternating sides of the terminal.

## Configuring Effects

All effect configuration options are available within each effect via the `effect.effect_config` and `effect.terminal_config` attributes.

=== "Syntax"

    ```python
    from terminaltexteffects.effects.effect_slide import Slide
    from terminaltexteffects.utils.graphics import Color

    text = ("EXAMPLE" * 10 + "\n") * 10

    effect = Slide(text)
    effect.effect_config.merge = True  # (1)
    effect.effect_config.grouping = "column"  # (2)
    effect.effect_config.final_gradient_stops = (Color("#0ff000"), Color("#000ff0"), Color("#0f00f0"))  # (3)
    effect.terminal_config.canvas_width = 30  # (4)
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)
    ```
    
    1. Use the `effect_config` attribute to modify the effect configuration. Setting `merge` to `True` on the Slide effect causes the text to slide
    in from alternating sides of the terminal.
    2. Columns will slide in, rather than rows.
    3. Change the gradient colors from the defaults.
    4. Set the canvas width manually rather than automatically detect. Canvas height will be automatically set to the input text height.

=== "Output"
    ![t](./img/lib_demos/libguide_configuration_output.gif)

## Configuring the Terminal/Canvas

### Terminal/Canvas Dimensions

TTE uses a [Terminal](./engine/terminal/terminal.md) class and a [Canvas](./engine/terminal/canvas.md) class to handle terminal/canvas dimensions, wrapping text, etc. Effects contain an attribute (`effect.terminal_config`) which allows access to the various terminal configuration options. The configuration should be modified prior to iterating over the effect.

For example, to set the Canvas dimensions manually:

```python
effect.terminal_config.canvas_width = 80
effect.terminal_config.canvas_height = 24
```

If either `canvas_width` or `canvas_height` are set to `0`, that dimension will be automatically detected based on the
terminal device dimensions. If either dimensions is set to `-1`, that dimensions will be set to match the input text dimensions.

By default, if your Canvas dimensions exceed the visible area of the Terminal, the text outside of that area will not be
output in the frame. If you want to output all characters regardless of they position relative to the visible terminal
area, set `terminal_config.ignore_terminal_dimensions` to `True`. This should **only** be used if you are handing the
frame yourself and outputting somewhere other than the terminal. The terminal emulator will wrap the text and produce
unexpected results.

```python
effect.terminal_config.ignore_terminal_dimensions = True
```

### Frame Rate

TTE sets a default target frame rate of 100FPS. To configure this within your scripts, access the
`effect.terminal_config.frame_rate` attribute. Set this attribute to `0` to remove the frame limit.

For more information on terminal configuration options, check out the [TerminalConfig](./engine/terminal/terminalconfig.md) reference.

## Infinitely Looping Effects

Some effects support infinite looping. For example, [ColorShift](./effects/colorshift.md) via the
[ColorShiftConfig.cycles](./effects/colorshift.md#terminaltexteffects.effects.effect_colorshift.ColorShiftConfig) config
attribute. When set to 0 directly, the effect will cycle indefinitely. Explore the configuration options for a given
effect to see if it supports infinite looping.

!!! note

    Infinite looping is *NOT* supported when TTE is run as an application. The command line argument validators will not accept these values. This is by design, to prevent users inadvertently inputting a configuration that results in having to interrupt the process to end an effect.
