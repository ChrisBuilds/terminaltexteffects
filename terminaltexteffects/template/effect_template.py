"""
Effect Description.

Classes:

"""

from __future__ import annotations

import typing
from dataclasses import dataclass

import terminaltexteffects.utils.argvalidators as argvalidators
from terminaltexteffects import Color, EffectCharacter, Gradient, easing
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return NamedEffect, EffectConfig


@argclass(
    name="namedeffect",
    help="effect_description",
    description="effect_description",
    epilog=f"""{argvalidators.EASING_EPILOG}
    """,
)
@dataclass
class EffectConfig(ArgsDataClass):
    color_single: Color = ArgField(
        cmd_name=["--color-single"],
        type_parser=argvalidators.ColorArg.type_parser,
        default=Color(0),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Color for the ___.",
    )  # type: ignore[assignment]
    "Color: Color for the ___."

    final_gradient_stops: tuple[Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("8A008A"), Color("00D1FF"), Color("FFFFFF")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[Color, ...]: Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] | int = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] | int: Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_frames: int = ArgField(
        cmd_name="--final-gradient-frames",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=5,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step. Increase to slow down the gradient animation.",
    )  # type: ignore[assignment]
    "int: Number of frames to display each gradient step. Increase to slow down the gradient animation."

    final_gradient_direction: Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=Gradient.Direction.VERTICAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "Gradient.Direction : Direction of the final gradient."

    movement_speed: float = ArgField(
        cmd_name="--movement-speed",
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=1,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Speed of the ___.",
    )  # type: ignore[assignment]
    "float: Speed of the ___."

    easing: easing.EasingFunction = ArgField(
        cmd_name=["--easing"],
        default=easing.in_out_sine,
        type_parser=argvalidators.Ease.type_parser,
        help="Easing function to use for character movement.",
    )  # type: ignore[assignment]
    "easing.EasingFunction: Easing function to use for character movement."

    @classmethod
    def get_effect_class(cls):
        return NamedEffect


class NamedEffectIterator(BaseEffectIterator[EffectConfig]):
    def __init__(self, effect: "NamedEffect") -> None:
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.build()

    def build(self) -> None:
        final_gradient = Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.text_bottom,
            self.terminal.canvas.text_top,
            self.terminal.canvas.text_left,
            self.terminal.canvas.text_right,
            self.config.final_gradient_direction,
        )
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]

            # do something with the data if needed (sort, adjust positions, etc)

    def __next__(self) -> str:
        if self.pending_chars or self.active_characters:
            # perform effect logic
            self.update()
            return self.frame
        else:
            raise StopIteration


class NamedEffect(BaseEffect[EffectConfig]):
    """Effect description."""

    _config_cls = EffectConfig
    _iterator_cls = NamedEffectIterator

    def __init__(self, input_data: str) -> None:
        """Initialize the effect with the provided input data.

        Args:
            input_data (str): The input data to use for the effect."""
        super().__init__(input_data)
