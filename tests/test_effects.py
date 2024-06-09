from terminaltexteffects.effects import (
    effect_beams,
    effect_binarypath,
    effect_blackhole,
    effect_bouncyballs,
    effect_bubbles,
    effect_burn,
    effect_colorshift,
    effect_crumble,
    effect_decrypt,
    effect_errorcorrect,
    effect_expand,
    effect_fireworks,
    effect_matrix,
    effect_middleout,
    effect_orbittingvolley,
    effect_overflow,
    effect_pour,
    effect_print,
    effect_rain,
    effect_random_sequence,
    effect_rings,
    effect_scattered,
    effect_slice,
    effect_slide,
    effect_spotlights,
    effect_spray,
    effect_swarm,
    effect_synthgrid,
    effect_unstable,
    effect_vhstape,
    effect_waves,
    effect_wipe,
)
from terminaltexteffects.engine.terminal import TerminalConfig

t1 = ""
t2 = "a"
t3 = """
a
b
c
d
e
f"""
t4 = "abcdefg"
t5 = """
0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ
123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0
23456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01
3456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ012
456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123
56789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01234
6789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ012345
789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456
89abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01234567
9abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ012345678
"""
t6 = """Tabs\tTabs\t\tTabs\t\t\tTabs"""
test_inputs = [t1, t2, t3, t4, t5, t6]


terminal_config = TerminalConfig()
terminal_config.frame_rate = 0
terminal_config.ignore_terminal_dimensions = True


def test_beams_effect() -> None:
    for input_data in test_inputs:
        effect = effect_beams.Beams(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_binarypath_effect() -> None:
    for input_data in test_inputs:
        effect = effect_binarypath.BinaryPath(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_blackhole_effect() -> None:
    for input_data in test_inputs:
        effect = effect_blackhole.Blackhole(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_bouncyballs_effect() -> None:
    for input_data in test_inputs:
        effect = effect_bouncyballs.BouncyBalls(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_bubbles_effect() -> None:
    for input_data in test_inputs:
        effect = effect_bubbles.Bubbles(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_burn_effect() -> None:
    for input_data in test_inputs:
        effect = effect_burn.Burn(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_colorshift_effect() -> None:
    for input_data in test_inputs:
        effect = effect_colorshift.ColorShift(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_crumble_effect() -> None:
    for input_data in test_inputs:
        effect = effect_crumble.Crumble(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_decrypt_effect() -> None:
    for input_data in test_inputs:
        effect = effect_decrypt.Decrypt(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_errorcorrect_effect() -> None:
    for input_data in test_inputs:
        effect = effect_errorcorrect.ErrorCorrect(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_expand_effect() -> None:
    for input_data in test_inputs:
        effect = effect_expand.Expand(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_fireworks_effect() -> None:
    for input_data in test_inputs:
        effect = effect_fireworks.Fireworks(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_matrix_effect() -> None:
    for input_data in test_inputs:
        effect = effect_matrix.Matrix(input_data)
        effect.terminal_config = terminal_config
        effect.effect_config.rain_time = 1
        for _ in effect:
            ...


def test_middleout_effect() -> None:
    for input_data in test_inputs:
        effect = effect_middleout.MiddleOut(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_orbittingvolley_effect() -> None:
    for input_data in test_inputs:
        effect = effect_orbittingvolley.OrbittingVolley(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_overflow_effect() -> None:
    for input_data in test_inputs:
        effect = effect_overflow.Overflow(input_data)
        for _ in effect:
            pass


def test_pour_effect() -> None:
    for input_data in test_inputs:
        effect = effect_pour.Pour(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_print_effect() -> None:
    for input_data in test_inputs:
        effect = effect_print.Print(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_rain_effect() -> None:
    for input_data in test_inputs:
        effect = effect_rain.Rain(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_randomsequence_effect() -> None:
    for input_data in test_inputs:
        effect = effect_random_sequence.RandomSequence(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_rings_effect() -> None:
    for input_data in test_inputs:
        effect = effect_rings.Rings(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_scattered_effect() -> None:
    for input_data in test_inputs:
        effect = effect_scattered.Scattered(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_slide_effect() -> None:
    for input_data in test_inputs:
        effect = effect_slide.Slide(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_spotlights_effect() -> None:
    for input_data in test_inputs:
        effect = effect_spotlights.Spotlights(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_spray_effect() -> None:
    for input_data in test_inputs:
        effect = effect_spray.Spray(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_swarm_effect() -> None:
    for input_data in test_inputs:
        effect = effect_swarm.Swarm(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_synthgrid_effect() -> None:
    for input_data in test_inputs:
        effect = effect_synthgrid.SynthGrid(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_unstable_effect() -> None:
    for input_data in test_inputs:
        effect = effect_unstable.Unstable(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_slice_effect() -> None:
    for input_data in test_inputs:
        effect = effect_slice.Slice(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_vhstape_effect() -> None:
    for input_data in test_inputs:
        effect = effect_vhstape.VHSTape(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_waves_effect() -> None:
    for input_data in test_inputs:
        effect = effect_waves.Waves(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_wipe_effect() -> None:
    for input_data in test_inputs:
        effect = effect_wipe.Wipe(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            ...


def test_terminal_xterm_colors() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        terminal_config.xterm_colors = True
        terminal_config.frame_rate = 0
        terminal_config.ignore_terminal_dimensions = True
        effect = effect_wipe.Wipe(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            pass


def test_terminal_no_color() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        terminal_config.no_color = True
        terminal_config.ignore_terminal_dimensions = True
        effect = effect_wipe.Wipe(input_data)
        effect.terminal_config = terminal_config
        for _ in effect:
            pass
