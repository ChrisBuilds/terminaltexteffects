from argparse import Namespace

from terminaltexteffects.effects import (
    effect_blackhole,
    effect_columnslide,
    effect_decrypt,
    effect_expand,
    effect_pour,
    effect_rain,
    effect_random_sequence,
    effect_rowmerge,
    effect_rowslide,
    effect_scattered,
    effect_bouncyballs,
    effect_spray,
    effect_verticalslice,
    effect_burn,
    effect_fireworks,
    effect_unstable,
    effect_bubbles,
    effect_middleout,
    effect_errorcorrect,
    effect_swarm,
    effect_crumble,
    effect_rings,
    effect_vhstape,
)
from terminaltexteffects.utils.terminal import Terminal
from terminaltexteffects.utils import easing

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


def make_args() -> Namespace:
    args = Namespace()
    args.no_color = False
    args.no_wrap = False
    args.xterm_colors = False
    args.tab_width = 4
    args.animation_rate = 0
    args.movement_speed = 3
    args.easing = easing.in_sine
    return args


def test_vhstape_effect() -> None:
    for input_data in test_inputs:
        args = make_args()
        args.base_color = "ffffff"
        args.final_color = "ffffff"
        args.glitch_line_colors = ["ffffff", "ff0000", "00ff00", "0000ff", "ffffff"]
        args.glitch_wave_colors = ["ffffff", "ff0000", "00ff00", "0000ff", "ffffff"]
        args.noise_colors = ["1e1e1f", "3c3b3d", "6d6c70", "a2a1a6", "cbc9cf", "ffffff"]
        args.glitch_line_chance = 0.005
        args.noise_chance = 0.004
        args.total_glitch_time = 200
        terminal = Terminal(input_data, args)
        vhstape_effect = effect_vhstape.VHSTapeEffect(terminal, args)
        vhstape_effect.run()


def test_rings_effect() -> None:
    for input_data in test_inputs:
        args = make_args()
        args.ring_colors = ["ff0000", "00ff00", "0000ff"]
        args.base_color = "ffffff"
        args.ring_gap = 5
        args.spin_duration = 10
        args.disperse_duration = 10
        args.spin_disperse_cycles = 2
        terminal = Terminal(input_data, args)
        rings_effect = effect_rings.RingsEffect(terminal, args)
        rings_effect.run()


def test_crumble_effect() -> None:
    for input_data in test_inputs:
        args = make_args()
        args.initial_color = "0088bb"
        args.dust_colors = ["dadad1", "766b69", "848789", "747a8a"]
        args.final_color = "0eeaff"
        terminal = Terminal(input_data, args)
        crumble_effect = effect_crumble.CrumbleEffect(terminal, args)
        crumble_effect.run()


def test_swarm_effect() -> None:
    for input_data in test_inputs:
        args = make_args()
        args.base_color = "ffffff"
        args.flash_color = "ff0000"
        args.final_color = "ffffff"
        args.swarm_size = 5
        args.swarm_coordination = 80
        terminal = Terminal(input_data, args)
        swarm_effect = effect_swarm.SwarmEffect(terminal, args)
        swarm_effect.run()


def test_errorcorrect_effect() -> None:
    for input_data in test_inputs:
        args = make_args()
        args.error_pairs = 12
        args.swap_delay = 70
        args.error_color = "e74c3c"
        args.correct_color = "45bf55"
        args.final_color = "ffffff"
        args.movement_speed = 0.5
        terminal = Terminal(input_data, args)
        errorcorrect_effect = effect_errorcorrect.ErrorCorrectEffect(terminal, args)
        errorcorrect_effect.run()


def test_middleout_effect() -> None:
    for input_data in test_inputs:
        args = make_args()
        args.starting_color = "ffffff"
        args.center_expand_color = "00ff00"
        args.full_expand_color = "0000ff"
        args.expand_direction = "vertical"
        args.center_movement_speed = 0.35
        args.full_movement_speed = 0.35
        args.center_easing = easing.in_out_sine
        args.full_easing = easing.in_out_sine
        terminal = Terminal(input_data, args)
        middleout_effect = effect_middleout.MiddleoutEffect(terminal, args)
        middleout_effect.run()


def test_blackhole_effect() -> None:
    for input_data in test_inputs:
        args = make_args()
        args.star_colors = ["000000"]
        args.blackhole_color = "ffffff"
        args.final_color = "ffffff"
        terminal = Terminal(input_data, args)
        blackhole_effect = effect_blackhole.BlackholeEffect(terminal, args)
        blackhole_effect.run()


def test_bubbles_effect() -> None:
    for input_data in test_inputs:
        args = make_args()
        args.final_color = "ffffff"
        args.pop_color = "ff0000"
        args.bubble_speed = 0.1
        args.bubble_delay = 1
        args.pop_condition = "row"
        args.no_rainbow = False
        terminal = Terminal(input_data, args)
        bubbles_effect = effect_bubbles.BubblesEffect(terminal, args)
        bubbles_effect.run()


def test_unstable_effect() -> None:
    for input_data in test_inputs:
        args = make_args()
        args.initial_color = "ffffff"
        args.unstable_color = "ff9200"
        args.final_color = "ffffff"
        args.explosion_ease = easing.out_expo
        args.explosion_speed = 0.75
        args.reassembly_ease = easing.out_expo
        args.reassembly_speed = 0.75
        terminal = Terminal(input_data, args)
        unstable_effect = effect_unstable.UnstableEffect(terminal, args)
        unstable_effect.run()


def test_pour_effect() -> None:
    for input_data in test_inputs:
        args = make_args()
        args.pour_direction = effect_pour.PourDirection.DOWN
        terminal = Terminal(input_data, args)
        pour_effect = effect_pour.PourEffect(terminal, args)
        pour_effect.run()


def test_scattered_effect() -> None:
    for input_data in test_inputs:
        args = make_args()
        terminal = Terminal(input_data, args)
        scattered_effect = effect_scattered.ScatteredEffect(terminal, args)
        scattered_effect.run()


def test_expand_effect() -> None:
    for input_data in test_inputs:
        args = make_args()
        terminal = Terminal(input_data, args)
        expand_effect = effect_expand.ExpandEffect(terminal, args)
        expand_effect.run()


def test_random_sequence_effect() -> None:
    for input_data in test_inputs:
        args = make_args()
        args.fade_startcolor = "000000"
        args.fade_endcolor = "ffffff"
        args.fade_duration = 5
        terminal = Terminal(input_data, args)
        random_sequence_effect = effect_random_sequence.RandomSequence(terminal, args)
        random_sequence_effect.run()


def test_spray_effect() -> None:
    for input_data in test_inputs:
        args = make_args()
        args.spray_position = effect_spray.SprayPosition.SE
        args.spray_volume = 5
        args.spray_colors = ["fe0345", "03faf0", "34a00f"]
        args.final_color = "ff0000"
        terminal = Terminal(input_data, args)
        sparkler_effect = effect_spray.SprayEffect(terminal, args)
        sparkler_effect.run()


def test_rain_effect() -> None:
    for input_data in test_inputs:
        args = make_args()
        args.rain_colors = []
        args.final_color = "ffffff"
        terminal = Terminal(input_data, args)
        rain_effect = effect_rain.RainEffect(terminal, args)
        rain_effect.run()


def test_decrypt_effect() -> None:
    for input_data in test_inputs:
        args = make_args()
        args.ciphertext_color = 40
        args.plaintext_color = 208
        terminal = Terminal(input_data, args)
        decrypt_effect = effect_decrypt.DecryptEffect(terminal, args)
        decrypt_effect.run()


def test_bouncyballs_effect() -> None:
    for input_data in test_inputs:
        args = make_args()
        args.ball_colors = ["fe0345", "03faf0", "34a00f"]
        args.final_color = "ffffff"
        args.ball_delay = 5
        terminal = Terminal(input_data, args)
        bouncyballs_effect = effect_bouncyballs.BouncyBallsEffect(terminal, args)
        bouncyballs_effect.run()


def test_rowslide_effect() -> None:
    for input_data in test_inputs:
        args = make_args()
        args.slide_direction = effect_rowslide.SlideDirection.LEFT
        args.row_gap = 5
        terminal = Terminal(input_data, args)
        rowslide_effect = effect_rowslide.RowSlide(terminal, args)
        rowslide_effect.run()


def test_columnslide_effect() -> None:
    for input_data in test_inputs:
        args = make_args()
        args.slide_direction = effect_columnslide.SlideDirection.DOWN
        args.column_gap = 5
        terminal = Terminal(input_data, args)
        columnslide_effect = effect_columnslide.ColumnSlide(terminal, args)
        columnslide_effect.run()


def test_verticalslice_effect() -> None:
    for input_data in test_inputs:
        args = make_args()
        terminal = Terminal(input_data, args)
        verticalslice_effect = effect_verticalslice.VerticalSlice(terminal, args)
        verticalslice_effect.run()


def test_rowmerge_effect() -> None:
    for input_data in test_inputs:
        args = make_args()
        terminal = Terminal(input_data, args)
        rowmerge_effect = effect_rowmerge.RowMergeEffect(terminal, args)
        rowmerge_effect.run()


def test_burn_effect() -> None:
    for input_data in test_inputs:
        args = make_args()
        args.flame_color = "848484"
        args.burned_color = "ff9600"
        args.final_color = "ffffff"
        terminal = Terminal(input_data, args)
        burn_effect = effect_burn.BurnEffect(terminal, args)
        burn_effect.run()


def test_fireworks_effect() -> None:
    for input_data in test_inputs:
        args = make_args()
        args.firework_colors = ["fe0345", "03faf0", "34a00f"]
        args.final_color = "ffffff"
        args.explode_anywhere = False
        args.firework_symbol = "⯏"
        args.firework_volume = 8
        args.launch_delay = 30
        args.launch_easing = easing.out_expo
        args.launch_speed = 0.2
        args.explode_distance = 10
        args.explode_easing = easing.out_quad
        args.explode_speed = 0.3
        args.fall_easing = easing.in_out_cubic
        args.fall_speed = 0.4
        terminal = Terminal(input_data, args)
        fireworks_effect = effect_fireworks.FireworksEffect(terminal, args)
        fireworks_effect.run()
