from time import sleep
import terminaltexteffects.utils.terminaloperations as tops
from terminaltexteffects.effects import (
    effect_char,
    expand,
    pour,
    random_sequence,
    scattered,
    sparkler,
    rain,
    decrypt,
    shootingstar,
    rowslide,
    columnslide,
    verticalslice,
    rowmerge,
)


test_data = """
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
test_rows = """0000000000000000000000000a
1111111111111111111111111b
22222222222222222222222222c
333333333333333333333333333d
444444444444444444444444e
55555555555555555555555f
6666666666666666666666g"""


def show_all(input_data: str = test_data) -> None:
    pour_effect = pour.PouringEffect(input_data, animation_rate=0.008, pour_direction=pour.PourDirection.DOWN)
    pour_effect.run()
    sleep(1)
    scattered_effect = scattered.ScatteredEffect(input_data, animation_rate=0.01)
    scattered_effect.run()
    sleep(1)
    expand_effect = expand.ExpandEffect(input_data, animation_rate=0.01)
    expand_effect.run()
    sleep(1)
    random_sequence_effect = random_sequence.RandomSequence(input_data, animation_rate=0.003)
    random_sequence_effect.run()
    sleep(1)
    sparkler_effect = sparkler.SparklerEffect(
        input_data, animation_rate=0.01, sparkler_position=sparkler.SparklerPosition.SE
    )
    sparkler_effect.run()
    sleep(1)
    rain_effect = rain.RainEffect(input_data, animation_rate=0.01)
    rain_effect.run()
    sleep(1)
    decrypt_effect = decrypt.DecryptEffect(input_data, animation_rate=0.003)
    decrypt_effect.run()
    sleep(1)
    shootingstar_effect = shootingstar.ShootingStarEffect(input_data, animation_rate=0.01)
    shootingstar_effect.run()
    sleep(1)
    rowslide_effect = rowslide.RowSlide(input_data, animation_rate=0.003, SlideDirection=rowslide.SlideDirection.LEFT)
    rowslide_effect.run()
    sleep(1)
    columnslide_effect = columnslide.ColumnSlide(input_data, 0.003, columnslide.SlideDirection.DOWN)
    columnslide_effect.run()
    sleep(1)
    verticalslice_effect = verticalslice.VerticalSlice(input_data, 0.02)
    verticalslice_effect.run()
    sleep(1)
    rowmerge_effect = rowmerge.RowMergeEffect(input_data, animation_rate=0.003)
    rowmerge_effect.run()


def test_pour_effect(input_data: str = test_data) -> None:
    pour_effect = pour.PouringEffect(input_data, animation_rate=0, pour_direction=pour.PourDirection.DOWN)
    pour_effect.run()


def test_scattered_effect(input_data: str = test_data) -> None:
    scattered_effect = scattered.ScatteredEffect(input_data, animation_rate=0)
    scattered_effect.run()


def test_expand_effect(input_data: str = test_data) -> None:
    expand_effect = expand.ExpandEffect(input_data, animation_rate=0)
    expand_effect.run()


def test_random_sequence_effect(input_data: str = test_data) -> None:
    random_sequence_effect = random_sequence.RandomSequence(input_data, animation_rate=0)
    random_sequence_effect.run()


def test_sparkler_effect(input_data: str = test_data) -> None:
    sparkler_effect = sparkler.SparklerEffect(
        input_data, animation_rate=0, sparkler_position=sparkler.SparklerPosition.SE
    )
    sparkler_effect.run()


def test_rain_effect(input_data: str = test_data) -> None:
    rain_effect = rain.RainEffect(input_data, animation_rate=0)
    rain_effect.run()


def test_decrypt_effect(input_data: str = test_data) -> None:
    decrypt_effect = decrypt.DecryptEffect(input_data, animation_rate=0)
    decrypt_effect.run()


def test_shootingstar_effect(input_data: str = test_data) -> None:
    shootingstar_effect = shootingstar.ShootingStarEffect(input_data, animation_rate=0)
    shootingstar_effect.run()


def test_rowslide_effect(input_data: str = test_data) -> None:
    rowslide_effect = rowslide.RowSlide(input_data, animation_rate=0, SlideDirection=rowslide.SlideDirection.LEFT)
    rowslide_effect.run()


def test_columnslide_effect(input_data: str = test_data) -> None:
    columnslide_effect = columnslide.ColumnSlide(
        input_data, animation_rate=0, SlideDirection=columnslide.SlideDirection.DOWN
    )
    columnslide_effect.run()


def test_verticalslice_effect(input_data: str = test_data) -> None:
    verticalslice_effect = verticalslice.VerticalSlice(input_data, animation_rate=0)
    verticalslice_effect.run()


def test_rowmerge_effect(input_data: str = test_data) -> None:
    rowmerge_effect = rowmerge.RowMergeEffect(input_data, animation_rate=0)
    rowmerge_effect.run()


def test_terminaloperations():
    print("\n" * 5)
    top_left = effect_char.EffectCharacter("A", -1, -1)
    bottom_right = effect_char.EffectCharacter("B", 10, 1)
    tops.print_character(top_left)
    tops.print_character(bottom_right)


if __name__ == "__main__":
    show_all()
