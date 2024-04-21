from terminaltexteffects.effects import (
    effect_beams,
    effect_binarypath,
    effect_blackhole,
    effect_bouncyballs,
    effect_bubbles,
    effect_burn,
    effect_crumble,
    effect_decrypt,
    effect_errorcorrect,
    effect_expand,
    effect_fireworks,
    effect_middleout,
    effect_orbittingvolley,
    effect_overflow,
    effect_pour,
    effect_print,
    effect_rain,
    effect_random_sequence,
    effect_rings,
    effect_scattered,
    effect_slide,
    effect_spotlights,
    effect_spray,
    effect_swarm,
    effect_synthgrid,
    effect_unstable,
    effect_verticalslice,
    effect_vhstape,
    effect_waves,
    effect_wipe,
)
from terminaltexteffects.utils.terminal import TerminalConfig

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


TERMARGS = TerminalConfig()
TERMARGS.frame_rate = 0


def test_beams_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_beams.Beams(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_binarypath_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_binarypath.BinaryPath(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_blackhole_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_blackhole.BlackholeEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_bouncyballs_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_bouncyballs.BouncyBallsEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_bubbles_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_bubbles.BubblesEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_burn_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_burn.BurnEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_crumble_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_crumble.CrumbleEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_decrypt_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_decrypt.DecryptEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_errorcorrect_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_errorcorrect.ErrorCorrectEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_expand_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_expand.ExpandEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_fireworks_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_fireworks.FireworksEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_middleout_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_middleout.MiddleoutEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_orbittingvolley_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_orbittingvolley.OrbittingVolleyEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_overflow_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_overflow.OverflowEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_pour_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_pour.PourEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_print_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_print.PrintEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_rain_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_rain.RainEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_random_sequence_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_random_sequence.RandomSequence(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_rings_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_rings.RingsEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_scattered_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_scattered.ScatteredEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_slide_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_slide.SlideEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_spotlights_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_spotlights.SpotlightsEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_spray_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_spray.SprayEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_swarm_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_swarm.SwarmEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_synthgrid_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_synthgrid.SynthGridEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_unstable_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_unstable.UnstableEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_verticalslice_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_verticalslice.VerticalSlice(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_vhstape_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_vhstape.VHSTapeEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_waves_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_waves.WavesEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_wipe_effect() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        effect = effect_wipe.WipeEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_terminal_xterm_colors() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        terminal_config.xterm_colors = True
        effect = effect_wipe.WipeEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass


def test_terminal_no_color() -> None:
    for input_data in test_inputs:
        terminal_config = TerminalConfig()
        terminal_config.frame_rate = 0
        terminal_config.no_color = True
        effect = effect_wipe.WipeEffect(input_data, terminal_config=terminal_config)
        for _ in effect:
            pass
