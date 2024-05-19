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

![t](./img/lib_demos/animated_prompts_demo.gif)
