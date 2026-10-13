# Library Cookbook

Below you'll find examples of interesting ways to use the TTE library.

## Animated Prompts

You can use any effect to create an animated prompt by setting the `end_symbol` parameter of the `terminal_output()`
context manager to `" "`. Adjust the effect configuration to achieve a more responsive prompt.

```python
from terminaltexteffects.effects.effect_beams import Beams
from terminaltexteffects.effects.effect_slide import Slide


def slide_animated_prompt(prompt_text: str) -> str:
    effect = Slide(prompt_text)
    effect.effect_config.final_gradient_frames = 1
    with effect.terminal_output(end_symbol=" ") as terminal:
        for frame in effect:
            terminal.print(frame)
    return input()


def beams_animated_prompt(prompt_text: str) -> str:
    effect = Beams(prompt_text)
    effect.effect_config.final_gradient_frames = 1
    with effect.terminal_output(end_symbol=" ") as terminal:
        for frame in effect:
            terminal.print(frame)
    return input()


resp = slide_animated_prompt("Here's a sliding prompt:")
resp = beams_animated_prompt("Here's one with beams:")
```

### Output

![Animated prompts using the Slide and Beams effects](./img/lib_demos/animated_prompts_demo.gif)

## More Examples

- [Effects are Iterable](./libguide.md#effects-are-iterable): send frames to your own TUI, GUI, or other output.
- [Collecting Frames](./libguide.md#collecting-frames): render a fixed-size animation without a live terminal.
- [Colors and Gradients](./engine/utils/gradient.md): build gradients and map them across a canvas.
- [Character Orders](./engine/terminal/terminal.md#character-orders): select characters in rows, rings, or spirals.
- [ParticlePool](./engine/particles.md): reuse helper characters for sparks, smoke, and other short-lived visuals.
