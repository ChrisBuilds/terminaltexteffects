from argparse import Namespace

from terminaltexteffects.effects import (
    effect_columnslide,
    effect_decrypt,
    effect_expand,
    effect_pour,
    effect_rain,
    effect_random_sequence,
    effect_rowmerge,
    effect_rowslide,
    effect_scattered,
    effect_shootingstar,
    effect_spray,
    effect_verticalslice,
    effect_burn,
)
from terminaltexteffects.utils.terminal import Terminal

BLOCK = """
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


def make_args() -> Namespace:
    args = Namespace()
    args.no_color = False
    args.xterm_colors = False
    args.animation_rate = 0
    return args


def test_pour_effect(input_data: str = BLOCK) -> None:
    args = make_args()
    args.pour_direction = effect_pour.PourDirection.DOWN
    terminal = Terminal(input_data, args)
    pour_effect = effect_pour.PourEffect(terminal, args)
    pour_effect.run()


def test_scattered_effect(input_data: str = BLOCK) -> None:
    args = make_args()
    terminal = Terminal(input_data, args)
    scattered_effect = effect_scattered.ScatteredEffect(terminal, args)
    scattered_effect.run()


def test_expand_effect(input_data: str = BLOCK) -> None:
    args = make_args()
    terminal = Terminal(input_data, args)
    expand_effect = effect_expand.ExpandEffect(terminal, args)
    expand_effect.run()


def test_random_sequence_effect(input_data: str = BLOCK) -> None:
    args = make_args()
    args.fade_startcolor = "000000"
    args.fade_endcolor = "ffffff"
    args.fade_duration = 5
    terminal = Terminal(input_data, args)
    random_sequence_effect = effect_random_sequence.RandomSequence(terminal, args)
    random_sequence_effect.run()


def test_spray_effect(input_data: str = BLOCK) -> None:
    args = make_args()
    args.spray_position = effect_spray.SprayPosition.SE
    args.spray_colors = ["fe0345", "03faf0", "34a00f"]
    args.final_color = "ff0000"
    terminal = Terminal(input_data, args)
    sparkler_effect = effect_spray.SprayEffect(terminal, args)
    sparkler_effect.run()


def test_rain_effect(input_data: str = BLOCK) -> None:
    args = make_args()
    args.rain_colors = []
    args.final_color = "ffffff"
    terminal = Terminal(input_data, args)
    rain_effect = effect_rain.RainEffect(terminal, args)
    rain_effect.run()


def test_decrypt_effect(input_data: str = BLOCK, animation_rate=0) -> None:
    args = make_args()
    args.ciphertext_color = 40
    args.plaintext_color = 208
    terminal = Terminal(input_data, args)
    decrypt_effect = effect_decrypt.DecryptEffect(terminal, args)
    decrypt_effect.run()


def test_shootingstar_effect(input_data: str = BLOCK) -> None:
    args = make_args()
    terminal = Terminal(input_data, args)
    shootingstar_effect = effect_shootingstar.ShootingStarEffect(terminal, args)
    shootingstar_effect.run()


def test_rowslide_effect(input_data: str = BLOCK) -> None:
    args = make_args()
    args.slide_direction = effect_rowslide.SlideDirection.LEFT
    args.row_gap = 5
    terminal = Terminal(input_data, args)
    rowslide_effect = effect_rowslide.RowSlide(terminal, args)
    rowslide_effect.run()


def test_columnslide_effect(input_data: str = BLOCK) -> None:
    args = make_args()
    args.slide_direction = effect_columnslide.SlideDirection.DOWN
    args.column_gap = 5
    terminal = Terminal(input_data, args)
    columnslide_effect = effect_columnslide.ColumnSlide(terminal, args)
    columnslide_effect.run()


def test_verticalslice_effect(input_data: str = BLOCK) -> None:
    args = make_args()
    terminal = Terminal(input_data, args)
    verticalslice_effect = effect_verticalslice.VerticalSlice(terminal, args)
    verticalslice_effect.run()


def test_rowmerge_effect(input_data: str = BLOCK) -> None:
    args = make_args()
    terminal = Terminal(input_data, args)
    rowmerge_effect = effect_rowmerge.RowMergeEffect(terminal, args)
    rowmerge_effect.run()


def test_burn_effect(input_data: str = BLOCK) -> None:
    args = make_args()
    args.flame_color = "848484"
    args.burned_color = "ff9600"
    args.final_color = "ffffff"
    terminal = Terminal(input_data, args)
    burn_effect = effect_burn.BurnEffect(terminal, args)
    burn_effect.run()
