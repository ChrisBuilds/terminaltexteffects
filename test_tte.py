from time import sleep
import utils.terminaloperations as tops
from effects import (
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
test_rows = """0000000000000000000000000
1111111111111111111111111
22222222222222222222222222
333333333333333333333333333
444444444444444444444444
55555555555555555555555
6666666666666666666666"""


def test_all(input_data: str) -> None:
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


def main():
    input_data = tops.get_piped_input()
    if not input_data:
        input_data = test_rows
    test_all(input_data)
    # tte_effect = pour.PouringEffect(input_data, animation_rate=0.004, pour_direction=pour.PourDirection.DOWN)
    # tte_effect = scattered.ScatteredEffect(input_data, animation_rate=0.01)
    # tte_effect = expand.ExpandEffect(input_data, animation_rate=0.01)
    # tte_effect = random_sequence.RandomSequence(input_data, animation_rate=0.01)
    # tte_effect = sparkler.SparklerEffect(input_data, sparkler.SparklerPosition.SE, animation_rate=0.01)
    # tte_effect = rain.RainEffect(input_data, animation_rate=0.01)
    # tte_effect = decrypt.DecryptEffect(input_data, animation_rate=0.003)
    # tte_effect = shootingstar.ShootingStarEffect(input_data, animation_rate=0.01)
    # tte_effect = rowslide.RowSlide(input_data, animation_rate=0.003, SlideDirection=rowslide.SlideDirection.LEFT)
    # tte_effect = columnslide.ColumnSlide(input_data, 0.003, columnslide.SlideDirection.DOWN)
    # tte_effect = verticalslice.VerticalSlice(input_data, 0.02)
    # tte_effect.run()


if __name__ == "__main__":
    main()
