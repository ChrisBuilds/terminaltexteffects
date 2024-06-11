from terminaltexteffects.effects.effect_colorshift import ColorShift
from terminaltexteffects.utils.graphics import Gradient

text = "EXAMPLE" * 10

effect = ColorShift(text)
effect.effect_config.travel = True
effect.effect_config.travel_direction = Gradient.Direction.RADIAL
effect.effect_config.loop_gradient = True
effect.effect_config.cycles = 0
effect.effect_config.gradient_frames
effect.terminal_config.canvas_height = 1
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
