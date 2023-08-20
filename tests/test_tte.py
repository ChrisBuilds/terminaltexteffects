from time import sleep
from argparse import ArgumentParser, Namespace
from terminaltexteffects.utils.terminal import Terminal
from terminaltexteffects import base_character
from terminaltexteffects.effects import (
    effect_expand,
    effect_pour,
    effect_random_sequence,
    effect_scattered,
    effect_sparkler,
    effect_rain,
    effect_decrypt,
    effect_shootingstar,
    effect_rowslide,
    effect_columnslide,
    effect_verticalslice,
    effect_rowmerge,
)

testdata_large = "".join([letter * 210 for letter in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"])
testdata_block = """
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

testdata_small = """
012345
6789ab
cdefgh
"""

testdata_rows = """0000000000000000000000000a
1111111111111111111111111b
22222222222222222222222222c
333333333333333333333333333d
444444444444444444444444e
55555555555555555555555f
6666666666666666666666g"""

testdata_tall = """30
29
28
27
26
25
24
23
22
21
20
19
18
17
16
15
14
13
12
11
10
9
8
7
6
5
4
3
2
1"""


def show_all(input_data: str = testdata_block, animation_rate=0) -> None:
    parser = ArgumentParser()
    sub = parser.add_subparsers()
    effect_pour.add_arguments(sub)
    args = parser.parse_args(["pour", "-a", str(animation_rate)])
    terminal = Terminal(input_data)
    pour_effect = effect_pour.PourEffect(terminal, args)
    pour_effect.run()
    sleep(1)
    parser = ArgumentParser()
    sub = parser.add_subparsers()
    effect_scattered.add_arguments(sub)
    args = parser.parse_args(["scattered", "-a", str(animation_rate)])
    terminal = Terminal(input_data)
    scattered_effect = effect_scattered.ScatteredEffect(terminal, args)
    scattered_effect.run()
    sleep(1)
    parser = ArgumentParser()
    sub = parser.add_subparsers()
    effect_expand.add_arguments(sub)
    args = parser.parse_args(["expand", "-a", str(animation_rate)])
    terminal = Terminal(input_data)
    expand_effect = effect_expand.ExpandEffect(terminal, args)
    expand_effect.run()
    sleep(1)
    parser = ArgumentParser()
    sub = parser.add_subparsers()
    effect_random_sequence.add_arguments(sub)
    args = parser.parse_args(["randomsequence", "-a", str(animation_rate)])
    terminal = Terminal(input_data)
    random_sequence_effect = effect_random_sequence.RandomSequence(terminal, args)
    random_sequence_effect.run()
    sleep(1)
    parser = ArgumentParser()
    sub = parser.add_subparsers()
    effect_sparkler.add_arguments(sub)
    args = parser.parse_args(["sparkler", "-a", str(animation_rate)])
    terminal = Terminal(input_data)
    sparkler_effect = effect_sparkler.SparklerEffect(terminal, args)
    sparkler_effect.run()
    sleep(1)
    parser = ArgumentParser()
    sub = parser.add_subparsers()
    effect_rain.add_arguments(sub)
    args = parser.parse_args(["rain", "-a", str(animation_rate)])
    terminal = Terminal(input_data)
    rain_effect = effect_rain.RainEffect(terminal, args)
    rain_effect.run()
    sleep(1)
    parser = ArgumentParser()
    sub = parser.add_subparsers()
    effect_decrypt.add_arguments(sub)
    args = parser.parse_args(["decrypt", "-a", str(animation_rate)])
    terminal = Terminal(input_data)
    decrypt_effect = effect_decrypt.DecryptEffect(terminal, args)
    decrypt_effect.run()
    sleep(1)
    parser = ArgumentParser()
    sub = parser.add_subparsers()
    effect_shootingstar.add_arguments(sub)
    args = parser.parse_args(["shootingstar", "-a", str(animation_rate)])
    terminal = Terminal(input_data)
    shootingstar_effect = effect_shootingstar.ShootingStarEffect(terminal, args)
    shootingstar_effect.run()
    sleep(1)
    parser = ArgumentParser()
    sub = parser.add_subparsers()
    effect_rowslide.add_arguments(sub)
    args = parser.parse_args(["rowslide", "-a", str(animation_rate)])
    terminal = Terminal(input_data)
    rowslide_effect = effect_rowslide.RowSlide(terminal, args)
    rowslide_effect.run()
    sleep(1)
    parser = ArgumentParser()
    sub = parser.add_subparsers()
    effect_columnslide.add_arguments(sub)
    args = parser.parse_args(["columnslide", "-a", str(animation_rate)])
    terminal = Terminal(input_data)
    columnslide_effect = effect_columnslide.ColumnSlide(terminal, args)
    columnslide_effect.run()
    sleep(1)
    parser = ArgumentParser()
    sub = parser.add_subparsers()
    effect_verticalslice.add_arguments(sub)
    args = parser.parse_args(["verticalslice", "-a", str(animation_rate)])
    terminal = Terminal(input_data)
    verticalslice_effect = effect_verticalslice.VerticalSlice(terminal, args)
    verticalslice_effect.run()
    sleep(1)
    parser = ArgumentParser()
    sub = parser.add_subparsers()
    effect_rowmerge.add_arguments(sub)
    args = parser.parse_args(["rowmerge", "-a", str(animation_rate)])
    terminal = Terminal(input_data)
    rowmerge_effect = effect_rowmerge.RowMergeEffect(terminal, args)
    rowmerge_effect.run()


def test_pour_effect(input_data: str = testdata_block, animation_rate: int = 0) -> None:
    args = Namespace(animation_rate=animation_rate)
    args.pour_direction = effect_pour.PourDirection.DOWN
    terminal = Terminal(input_data)
    pour_effect = effect_pour.PourEffect(terminal, args)
    pour_effect.run()


def test_scattered_effect(input_data: str = testdata_block, animation_rate: int = 0) -> None:
    args = Namespace(animation_rate=animation_rate)
    terminal = Terminal(input_data)
    scattered_effect = effect_scattered.ScatteredEffect(terminal, args)
    scattered_effect.run()


def test_expand_effect(input_data: str = testdata_block, animation_rate: int = 0) -> None:
    args = Namespace(animation_rate=animation_rate)
    terminal = Terminal(input_data)
    expand_effect = effect_expand.ExpandEffect(terminal, args)
    expand_effect.run()


def test_random_sequence_effect(input_data: str = testdata_block, animation_rate: int = 0) -> None:
    args = Namespace(animation_rate=animation_rate)
    terminal = Terminal(input_data)
    random_sequence_effect = effect_random_sequence.RandomSequence(terminal, args)
    random_sequence_effect.run()


def test_sparkler_effect(input_data: str = testdata_block, animation_rate: int = 0) -> None:
    args = Namespace(animation_rate=animation_rate)
    args.sparkler_position = effect_sparkler.SparklerPosition.SE
    terminal = Terminal(input_data)
    sparkler_effect = effect_sparkler.SparklerEffect(terminal, args)
    sparkler_effect.run()


def test_rain_effect(input_data: str = testdata_block, animation_rate: int = 0) -> None:
    args = Namespace(animation_rate=animation_rate)
    terminal = Terminal(input_data)
    rain_effect = effect_rain.RainEffect(terminal, args)
    rain_effect.run()


def test_decrypt_effect(input_data: str = testdata_block, animation_rate=0) -> None:
    args = Namespace(animation_rate=animation_rate)
    terminal = Terminal(input_data)
    args.ciphertext_color = 40
    args.plaintext_color = 208
    decrypt_effect = effect_decrypt.DecryptEffect(terminal, args)
    decrypt_effect.run()


def test_shootingstar_effect(input_data: str = testdata_block, animation_rate: int = 0) -> None:
    args = Namespace(animation_rate=animation_rate)
    terminal = Terminal(input_data)
    shootingstar_effect = effect_shootingstar.ShootingStarEffect(terminal, args)
    shootingstar_effect.run()


def test_rowslide_effect(input_data: str = testdata_block, animation_rate: int = 0) -> None:
    args = Namespace(animation_rate=animation_rate)
    args.slide_direction = effect_rowslide.SlideDirection.LEFT
    terminal = Terminal(input_data)
    rowslide_effect = effect_rowslide.RowSlide(terminal, args)
    rowslide_effect.run()


def test_columnslide_effect(input_data: str = testdata_block, animation_rate: int = 0) -> None:
    args = Namespace(animation_rate=animation_rate)
    args.slide_direction = effect_columnslide.SlideDirection.DOWN
    terminal = Terminal(input_data)
    columnslide_effect = effect_columnslide.ColumnSlide(terminal, args)
    columnslide_effect.run()


def test_verticalslice_effect(input_data: str = testdata_block, animation_rate: int = 0) -> None:
    args = Namespace(animation_rate=animation_rate)
    terminal = Terminal(input_data)
    verticalslice_effect = effect_verticalslice.VerticalSlice(terminal, args)
    verticalslice_effect.run()


def test_rowmerge_effect(input_data: str = testdata_block, animation_rate: int = 0) -> None:
    args = Namespace(animation_rate=animation_rate)
    terminal = Terminal(input_data)
    rowmerge_effect = effect_rowmerge.RowMergeEffect(terminal, args)
    rowmerge_effect.run()


def main():
    input_data = testdata_large
    show_all(input_data)


if __name__ == "__main__":
    main()
