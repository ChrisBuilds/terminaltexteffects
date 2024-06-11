from __future__ import annotations

import typing
from dataclasses import dataclass

import terminaltexteffects.utils.argvalidators as argvalidators
from terminaltexteffects.engine.base_character import EffectCharacter
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return Test, TestConfig


@argclass(
    name="test",
    help="effect_description",
    description="effect_description",
    epilog=f"""{argvalidators.EASING_EPILOG}
    """,
)
@dataclass
class TestConfig(ArgsDataClass):
    color_single: graphics.Color = ArgField(
        cmd_name=["--color-single"],
        type_parser=argvalidators.ColorArg.type_parser,
        default=0,
        metavar=argvalidators.ColorArg.METAVAR,
        help="Color for the ___.",
    )  # type: ignore[assignment]
    color_list: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--color-list"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=0,
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the ___.",
    )  # type: ignore[assignment]
    final_color: graphics.Color = ArgField(
        cmd_name=["--final-color"],
        type_parser=argvalidators.ColorArg.type_parser,
        default="ffffff",
        metavar=argvalidators.ColorArg.METAVAR,
        help="Color for the final character.",
    )  # type: ignore[assignment]
    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=("8A008A", "00D1FF", "FFFFFF"),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    final_gradient_frames: int = ArgField(
        cmd_name="--final-gradient-frames",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=5,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step.",
    )  # type: ignore[assignment]
    movement_speed: float = ArgField(
        cmd_name="--movement-speed",
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=1,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Speed of the ___.",
    )  # type: ignore[assignment]
    easing: typing.Callable = ArgField(
        cmd_name=["--easing"],
        default=easing.in_out_sine,
        type_parser=argvalidators.Ease.type_parser,
        help="Easing function to use for character movement.",
    )  # type: ignore[assignment]

    @classmethod
    def get_effect_class(cls):
        return Test


class TestIterator(BaseEffectIterator[TestConfig]):
    def __init__(self, effect: "Test") -> None:
        super().__init__(effect)
        self.pending_groups: list[list[EffectCharacter]] = []
        self.active_chars: list[EffectCharacter] = []
        self.build()

    def build(self) -> None:
        # g = graphics.Gradient("000000", "ffffff", steps=3)
        # for character in self.terminal.get_characters():
        #     for color in g:
        #         character.animation.set_appearance(character.input_symbol, color=color)
        #     self._pending_chars.append(character)
        for character_group in self.terminal.get_characters_grouped(
            self.terminal.CharacterGroup.DIAGONAL_BOTTOM_LEFT_TO_TOP_RIGHT
        ):
            self.pending_groups.append(character_group)
        self.current_group = self.pending_groups.pop(0)

    def __next__(self) -> str:
        if self.pending_groups or self.active_chars or self.current_group:
            if not self.current_group and self.pending_groups:
                self.current_group = self.pending_groups.pop(0)
            if self.current_group:
                next_char = self.current_group.pop(0)
                self.terminal.set_character_visibility(next_char, True)
                self.active_chars.append(next_char)

            self.update()
            return self.frame
        else:
            raise StopIteration


class Test(BaseEffect[TestConfig]):
    _config_cls = TestConfig
    _iterator_cls = TestIterator

    def __init__(self, input_data: str) -> None:
        super().__init__(input_data)
