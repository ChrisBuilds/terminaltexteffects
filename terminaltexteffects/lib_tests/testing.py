from terminaltexteffects.effects.effect_matrix import Matrix

effect = Matrix("YourTextHere\n" * 10)
effect.effect_config.rain_time = 0
with effect.terminal_output() as terminal:
    for frame in effect:
        terminal.print(frame)
