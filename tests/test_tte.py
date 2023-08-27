from argparse import ArgumentParser, Namespace
from time import sleep

from terminaltexteffects import base_character
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

testdata_title3 = r"""
 ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄       ▄  ▄▄▄▄▄▄▄▄▄▄▄       ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄ 
▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░▌     ▐░▌▐░░░░░░░░░░░▌     ▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌
 ▀▀▀▀█░█▀▀▀▀ ▐░█▀▀▀▀▀▀▀▀▀  ▐░▌   ▐░▌  ▀▀▀▀█░█▀▀▀▀      ▐░█▀▀▀▀▀▀▀▀▀ ▐░█▀▀▀▀▀▀▀▀▀ ▐░█▀▀▀▀▀▀▀▀▀ ▐░█▀▀▀▀▀▀▀▀▀ ▐░█▀▀▀▀▀▀▀▀▀  ▀▀▀▀█░█▀▀▀▀ ▐░█▀▀▀▀▀▀▀▀▀ 
     ▐░▌     ▐░▌            ▐░▌ ▐░▌       ▐░▌          ▐░▌          ▐░▌          ▐░▌          ▐░▌          ▐░▌               ▐░▌     ▐░▌          
     ▐░▌     ▐░█▄▄▄▄▄▄▄▄▄    ▐░▐░▌        ▐░▌          ▐░█▄▄▄▄▄▄▄▄▄ ▐░█▄▄▄▄▄▄▄▄▄ ▐░█▄▄▄▄▄▄▄▄▄ ▐░█▄▄▄▄▄▄▄▄▄ ▐░▌               ▐░▌     ▐░█▄▄▄▄▄▄▄▄▄ 
     ▐░▌     ▐░░░░░░░░░░░▌    ▐░▌         ▐░▌          ▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░▌               ▐░▌     ▐░░░░░░░░░░░▌
     ▐░▌     ▐░█▀▀▀▀▀▀▀▀▀    ▐░▌░▌        ▐░▌          ▐░█▀▀▀▀▀▀▀▀▀ ▐░█▀▀▀▀▀▀▀▀▀ ▐░█▀▀▀▀▀▀▀▀▀ ▐░█▀▀▀▀▀▀▀▀▀ ▐░▌               ▐░▌      ▀▀▀▀▀▀▀▀▀█░▌
     ▐░▌     ▐░▌            ▐░▌ ▐░▌       ▐░▌          ▐░▌          ▐░▌          ▐░▌          ▐░▌          ▐░▌               ▐░▌               ▐░▌
     ▐░▌     ▐░█▄▄▄▄▄▄▄▄▄  ▐░▌   ▐░▌      ▐░▌          ▐░█▄▄▄▄▄▄▄▄▄ ▐░▌          ▐░▌          ▐░█▄▄▄▄▄▄▄▄▄ ▐░█▄▄▄▄▄▄▄▄▄      ▐░▌      ▄▄▄▄▄▄▄▄▄█░▌
     ▐░▌     ▐░░░░░░░░░░░▌▐░▌     ▐░▌     ▐░▌          ▐░░░░░░░░░░░▌▐░▌          ▐░▌          ▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌     ▐░▌     ▐░░░░░░░░░░░▌
      ▀       ▀▀▀▀▀▀▀▀▀▀▀  ▀       ▀       ▀            ▀▀▀▀▀▀▀▀▀▀▀  ▀            ▀            ▀▀▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀▀▀▀▀▀       ▀       ▀▀▀▀▀▀▀▀▀▀▀ 
"""
testdata_title2 = r"""
  ::::::::::: :::::::::: :::    ::: :::::::::::          :::::::::: :::::::::: :::::::::: :::::::::: :::::::: ::::::::::: :::::::: 
     :+:     :+:        :+:    :+:     :+:              :+:        :+:        :+:        :+:       :+:    :+:    :+:    :+:    :+: 
    +:+     +:+         +:+  +:+      +:+              +:+        +:+        +:+        +:+       +:+           +:+    +:+         
   +#+     +#++:++#     +#++:+       +#+              +#++:++#   :#::+::#   :#::+::#   +#++:++#  +#+           +#+    +#++:++#++   
  +#+     +#+         +#+  +#+      +#+              +#+        +#+        +#+        +#+       +#+           +#+           +#+    
 #+#     #+#        #+#    #+#     #+#              #+#        #+#        #+#        #+#       #+#    #+#    #+#    #+#    #+#     
###     ########## ###    ###     ###              ########## ###        ###        ########## ########     ###     ########       
"""

testdata_title1 = r"""
 _________  _______      ___    ___ _________        _______   ________ ________ _______   ________ _________  ________      
|\___   ___\\  ___ \    |\  \  /  /|\___   ___\     |\  ___ \ |\  _____\\  _____\\  ___ \ |\   ____\\___   ___\\   ____\     
\|___ \  \_\ \   __/|   \ \  \/  / ||___ \  \_|     \ \   __/|\ \  \__/\ \  \__/\ \   __/|\ \  \___\|___ \  \_\ \  \___|_    
     \ \  \ \ \  \_|/__  \ \    / /     \ \  \       \ \  \_|/_\ \   __\\ \   __\\ \  \_|/_\ \  \       \ \  \ \ \_____  \   
      \ \  \ \ \  \_|\ \  /     \/       \ \  \       \ \  \_|\ \ \  \_| \ \  \_| \ \  \_|\ \ \  \____   \ \  \ \|____|\  \  
       \ \__\ \ \_______\/  /\   \        \ \__\       \ \_______\ \__\   \ \__\   \ \_______\ \_______\  \ \__\  ____\_\  \ 
        \|__|  \|_______/__/ /\ __\        \|__|        \|_______|\|__|    \|__|    \|_______|\|_______|   \|__| |\_________\
                        |__|/ \|__|                                                                              \|_________|
"""
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


def show_all(input_data: str = testdata_block) -> None:
    parser = ArgumentParser()
    sub = parser.add_subparsers()
    effect_pour.add_arguments(sub)
    args = parser.parse_args(["pour"])
    terminal = Terminal(input_data, False, args.animation_rate)
    pour_effect = effect_pour.PourEffect(terminal, args)
    pour_effect.run()
    sleep(0.5)
    parser = ArgumentParser()
    sub = parser.add_subparsers()
    effect_scattered.add_arguments(sub)
    args = parser.parse_args(["scattered"])
    terminal = Terminal(input_data, False, args.animation_rate)
    scattered_effect = effect_scattered.ScatteredEffect(terminal, args)
    scattered_effect.run()
    sleep(0.5)
    parser = ArgumentParser()
    sub = parser.add_subparsers()
    effect_expand.add_arguments(sub)
    args = parser.parse_args(["expand"])
    terminal = Terminal(input_data, False, args.animation_rate)
    expand_effect = effect_expand.ExpandEffect(terminal, args)
    expand_effect.run()
    sleep(0.5)
    parser = ArgumentParser()
    sub = parser.add_subparsers()
    effect_random_sequence.add_arguments(sub)
    args = parser.parse_args(["randomsequence"])
    terminal = Terminal(input_data, False, args.animation_rate)
    random_sequence_effect = effect_random_sequence.RandomSequence(terminal, args)
    random_sequence_effect.run()
    sleep(0.5)
    parser = ArgumentParser()
    sub = parser.add_subparsers()
    effect_spray.add_arguments(sub)
    args = parser.parse_args(["spray"])
    terminal = Terminal(input_data, False, args.animation_rate)
    sparkler_effect = effect_spray.SprayEffect(terminal, args)
    sparkler_effect.run()
    sleep(0.5)
    parser = ArgumentParser()
    sub = parser.add_subparsers()
    effect_rain.add_arguments(sub)
    args = parser.parse_args(["rain"])
    terminal = Terminal(input_data, False, args.animation_rate)
    rain_effect = effect_rain.RainEffect(terminal, args)
    rain_effect.run()
    sleep(0.5)
    parser = ArgumentParser()
    sub = parser.add_subparsers()
    effect_decrypt.add_arguments(sub)
    args = parser.parse_args(["decrypt"])
    terminal = Terminal(input_data, False, args.animation_rate)
    decrypt_effect = effect_decrypt.DecryptEffect(terminal, args)
    decrypt_effect.run()
    sleep(0.5)
    parser = ArgumentParser()
    sub = parser.add_subparsers()
    effect_shootingstar.add_arguments(sub)
    args = parser.parse_args(["shootingstar"])
    terminal = Terminal(input_data, False, args.animation_rate)
    shootingstar_effect = effect_shootingstar.ShootingStarEffect(terminal, args)
    shootingstar_effect.run()
    sleep(0.5)
    parser = ArgumentParser()
    sub = parser.add_subparsers()
    effect_rowslide.add_arguments(sub)
    args = parser.parse_args(["rowslide"])
    terminal = Terminal(input_data, False, args.animation_rate)
    rowslide_effect = effect_rowslide.RowSlide(terminal, args)
    rowslide_effect.run()
    sleep(0.5)
    parser = ArgumentParser()
    sub = parser.add_subparsers()
    effect_columnslide.add_arguments(sub)
    args = parser.parse_args(["columnslide"])
    terminal = Terminal(input_data, False, args.animation_rate)
    columnslide_effect = effect_columnslide.ColumnSlide(terminal, args)
    columnslide_effect.run()
    sleep(0.5)
    parser = ArgumentParser()
    sub = parser.add_subparsers()
    effect_verticalslice.add_arguments(sub)
    args = parser.parse_args(["verticalslice"])
    terminal = Terminal(input_data, False, args.animation_rate)
    verticalslice_effect = effect_verticalslice.VerticalSlice(terminal, args)
    verticalslice_effect.run()
    sleep(0.5)
    parser = ArgumentParser()
    sub = parser.add_subparsers()
    effect_rowmerge.add_arguments(sub)
    args = parser.parse_args(["rowmerge"])
    terminal = Terminal(input_data, False, args.animation_rate)
    rowmerge_effect = effect_rowmerge.RowMergeEffect(terminal, args)
    rowmerge_effect.run()
    sleep(0.5)
    parser = ArgumentParser()
    sub = parser.add_subparsers()
    effect_burn.add_arguments(sub)
    args = parser.parse_args(["burn"])
    terminal = Terminal(input_data, False, args.animation_rate)
    burn_effect = effect_burn.BurnEffect(terminal, args)
    burn_effect.run()


def test_pour_effect(input_data: str = testdata_block, animation_rate: int = 0) -> None:
    args = Namespace()
    args.pour_direction = effect_pour.PourDirection.DOWN
    terminal = Terminal(input_data, False, animation_rate)
    pour_effect = effect_pour.PourEffect(terminal, args)
    pour_effect.run()


def test_scattered_effect(input_data: str = testdata_block, animation_rate: int = 0) -> None:
    args = Namespace()
    terminal = Terminal(input_data, False, animation_rate)
    scattered_effect = effect_scattered.ScatteredEffect(terminal, args)
    scattered_effect.run()


def test_expand_effect(input_data: str = testdata_block, animation_rate: int = 0) -> None:
    args = Namespace()
    terminal = Terminal(input_data, False, animation_rate)
    expand_effect = effect_expand.ExpandEffect(terminal, args)
    expand_effect.run()


def test_random_sequence_effect(input_data: str = testdata_block, animation_rate: int = 0) -> None:
    args = Namespace()
    args.fade_startcolor = "000000"
    args.fade_endcolor = "ffffff"
    args.fade_duration = 5
    terminal = Terminal(input_data, False, animation_rate)
    random_sequence_effect = effect_random_sequence.RandomSequence(terminal, args)
    random_sequence_effect.run()


def test_spray_effect(input_data: str = testdata_block, animation_rate: int = 0) -> None:
    args = Namespace()
    args.spray_position = effect_spray.SprayPosition.SE
    args.spray_colors = ["fe0345", "03faf0", "34a00f"]
    args.final_color = "ff0000"
    terminal = Terminal(input_data, False, animation_rate)
    sparkler_effect = effect_spray.SprayEffect(terminal, args)
    sparkler_effect.run()


def test_rain_effect(input_data: str = testdata_block, animation_rate: int = 0) -> None:
    args = Namespace(animation_rate=animation_rate, rain_colors=[])
    args.final_color = "ffffff"
    terminal = Terminal(input_data, False, animation_rate)
    rain_effect = effect_rain.RainEffect(terminal, args)
    rain_effect.run()


def test_decrypt_effect(input_data: str = testdata_block, animation_rate=0) -> None:
    args = Namespace()
    terminal = Terminal(input_data, False, animation_rate)
    args.ciphertext_color = 40
    args.plaintext_color = 208
    decrypt_effect = effect_decrypt.DecryptEffect(terminal, args)
    decrypt_effect.run()


def test_shootingstar_effect(input_data: str = testdata_block, animation_rate: int = 0) -> None:
    args = Namespace()
    terminal = Terminal(input_data, False, animation_rate)
    shootingstar_effect = effect_shootingstar.ShootingStarEffect(terminal, args)
    shootingstar_effect.run()


def test_rowslide_effect(input_data: str = testdata_block, animation_rate: int = 0) -> None:
    args = Namespace()
    args.slide_direction = effect_rowslide.SlideDirection.LEFT
    terminal = Terminal(input_data, False, animation_rate)
    rowslide_effect = effect_rowslide.RowSlide(terminal, args)
    rowslide_effect.run()


def test_columnslide_effect(input_data: str = testdata_block, animation_rate: int = 0) -> None:
    args = Namespace()
    args.slide_direction = effect_columnslide.SlideDirection.DOWN
    terminal = Terminal(input_data, False, animation_rate)
    columnslide_effect = effect_columnslide.ColumnSlide(terminal, args)
    columnslide_effect.run()


def test_verticalslice_effect(input_data: str = testdata_block, animation_rate: int = 0) -> None:
    args = Namespace()
    terminal = Terminal(input_data, False, animation_rate)
    verticalslice_effect = effect_verticalslice.VerticalSlice(terminal, args)
    verticalslice_effect.run()


def test_rowmerge_effect(input_data: str = testdata_block, animation_rate: int = 0) -> None:
    args = Namespace()
    terminal = Terminal(input_data, False, animation_rate)
    rowmerge_effect = effect_rowmerge.RowMergeEffect(terminal, args)
    rowmerge_effect.run()


def test_burn_effect(input_data: str = testdata_block, animation_rate: int = 0) -> None:
    args = Namespace()
    args.flame_color = "848484"
    args.burned_color = "ff9600"
    args.final_color = "ffffff"
    terminal = Terminal(input_data, False, animation_rate)
    burn_effect = effect_burn.BurnEffect(terminal, args)
    burn_effect.run()


def main():
    input_data = testdata_title3
    show_all(input_data)


if __name__ == "__main__":
    main()
