from terminaltexteffects.effects.effect_beams import Beams
from terminaltexteffects.effects.effect_slide import Slide
from terminaltexteffects.utils.graphics import Gradient


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
    effect.effect_config.final_gradient_direction = Gradient.Direction.HORIZONTAL
    with effect.terminal_output(end_symbol=" ") as terminal:
        for frame in effect:
            terminal.print(frame)
    return input()


resp = slide_animated_prompt("Here's a sliding prompt:")
resp = beams_animated_prompt("Here's one with beams:")
