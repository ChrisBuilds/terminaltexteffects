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
from terminaltexteffects.utils.terminal import Terminal, TerminalConfig

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
TERMARGS.animation_rate = 0


def test_beams_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        beams_effect = effect_beams.BeamsEffect(terminal, effect_beams.BeamsEffectArgs())
        beams_effect.run()


def test_binarypath_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        binarypath_effect = effect_binarypath.BinaryPathEffect(terminal, effect_binarypath.BinaryPathEffectArgs())
        binarypath_effect.run()


def test_blackhole_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        blackhole_effect = effect_blackhole.BlackholeEffect(terminal, effect_blackhole.BlackholeEffectArgs())
        blackhole_effect.run()


def test_bouncyballs_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        bouncyballs_effect = effect_bouncyballs.BouncyBallsEffect(terminal, effect_bouncyballs.BouncyBallsEffectArgs())
        bouncyballs_effect.run()


def test_bubbles_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        bubbles_effect = effect_bubbles.BubblesEffect(terminal, effect_bubbles.BubblesEffectArgs())
        bubbles_effect.run()


def test_burn_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        burn_effect = effect_burn.BurnEffect(terminal, effect_burn.BurnEffectArgs())
        burn_effect.run()


def test_crumble_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        crumble_effect = effect_crumble.CrumbleEffect(terminal, effect_crumble.CrumbleEffectArgs())
        crumble_effect.run()


def test_decrypt_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        decrypt_effect = effect_decrypt.DecryptEffect(terminal, effect_decrypt.DecryptEffectArgs())
        decrypt_effect.run()


def test_errorcorrect_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        errorcorrect_effect = effect_errorcorrect.ErrorCorrectEffect(
            terminal, effect_errorcorrect.ErrorCorrectEffectArgs()
        )
        errorcorrect_effect.run()


def test_expand_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        expand_effect = effect_expand.ExpandEffect(terminal, effect_expand.ExpandEffectArgs())
        expand_effect.run()


def test_fireworks_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        fireworks_effect = effect_fireworks.FireworksEffect(terminal, effect_fireworks.FireworksEffectArgs())
        fireworks_effect.run()


def test_middleout_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        middleout_effect = effect_middleout.MiddleoutEffect(terminal, effect_middleout.MiddleoutEffectArgs())
        middleout_effect.run()


def test_orbittingvolley_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        orbittingvolley_effect = effect_orbittingvolley.OrbittingVolleyEffect(
            terminal, effect_orbittingvolley.OrbittingVolleyEffectArgs()
        )
        orbittingvolley_effect.run()


def test_overflow_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        overflow_effect = effect_overflow.OverflowEffect(terminal, effect_overflow.OverflowEffectArgs())
        overflow_effect.run()


def test_pour_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        pour_effect = effect_pour.PourEffect(terminal, effect_pour.PourEffectArgs())
        pour_effect.run()


def test_print_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        print_effect = effect_print.PrintEffect(terminal, effect_print.PrintEffectArgs())
        print_effect.run()


def test_rain_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        rain_effect = effect_rain.RainEffect(terminal, effect_rain.RainEffectArgs())
        rain_effect.run()


def test_random_sequence_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        random_sequence_effect = effect_random_sequence.RandomSequence(
            terminal, effect_random_sequence.RandomSequenceConfig()
        )
        random_sequence_effect.run()


def test_rings_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        rings_effect = effect_rings.RingsEffect(terminal, effect_rings.RingsEffectArgs())
        rings_effect.run()


def test_scattered_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        scattered_effect = effect_scattered.ScatteredEffect(terminal, effect_scattered.ScatteredEffectArgs())
        scattered_effect.run()


def test_slide_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        slide_effect = effect_slide.SlideEffect(terminal, effect_slide.SlideEffectArgs())
        slide_effect.run()


def test_spotlights_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        spotlights_effect = effect_spotlights.SpotlightsEffect(terminal, effect_spotlights.SpotlightsEffectArgs())
        spotlights_effect.run()


def test_spray_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        sparkler_effect = effect_spray.SprayEffect(terminal, effect_spray.SprayEffectArgs())
        sparkler_effect.run()


def test_swarm_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        swarm_effect = effect_swarm.SwarmEffect(terminal, effect_swarm.SwarmEffectArgs())
        swarm_effect.run()


def test_synthgrid_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        synthgrid_effect = effect_synthgrid.SynthGridEffect(terminal, effect_synthgrid.SynthGridEffectArgs())
        synthgrid_effect.run()


def test_unstable_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        unstable_effect = effect_unstable.UnstableEffect(terminal, effect_unstable.UnstableEffectArgs())
        unstable_effect.run()


def test_verticalslice_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        verticalslice_effect = effect_verticalslice.VerticalSlice(terminal, effect_verticalslice.VerticalSliceArgs())
        verticalslice_effect.run()


def test_vhstape_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        vhstape_effect = effect_vhstape.VHSTapeEffect(terminal, effect_vhstape.VHSTapeEffectArgs())
        vhstape_effect.run()


def test_waves_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        waves_effect = effect_waves.WavesEffect(terminal, effect_waves.WavesEffectArgs())
        waves_effect.run()


def test_wipe_effect() -> None:
    for input_data in test_inputs:
        terminal = Terminal(input_data, TERMARGS)
        wipe_effect = effect_wipe.WipeEffect(terminal, effect_wipe.WipeEffectArgs())
        wipe_effect.run()


def test_terminal_xterm_colors() -> None:
    terminal_args = TerminalConfig()
    terminal_args.xterm_colors = True
    terminal_args.animation_rate = 0
    for input_data in test_inputs:
        terminal = Terminal(input_data, terminal_args)
        wipe_effect = effect_wipe.WipeEffect(terminal, effect_wipe.WipeEffectArgs())
        wipe_effect.run()


def test_terminal_no_color() -> None:
    terminal_args = TerminalConfig()
    terminal_args.no_color = True
    terminal_args.animation_rate = 0
    for input_data in test_inputs:
        terminal = Terminal(input_data, terminal_args)
        wipe_effect = effect_wipe.WipeEffect(terminal, effect_wipe.WipeEffectArgs())
        wipe_effect.run()
