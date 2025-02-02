"""Effect Description.

Classes:

"""  # noqa: INP001

from __future__ import annotations

import typing
from dataclasses import dataclass

import terminaltexteffects as tte
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argvalidators
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    """Return the effect class and the effect configuration dataclass."""
    return Effect, EffectConfig


@argclass(
    name="namedeffect",
    help="effect_description",
    description="effect_description",
    epilog=f"""{argvalidators.EASING_EPILOG}
    """,
)
@dataclass
class EffectConfig(ArgsDataClass):
    """Effect configuration dataclass."""

    color_single: tte.Color = ArgField(
        cmd_name=["--color-single"],
        type_parser=argvalidators.ColorArg.type_parser,
        default=tte.Color(0),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Color for the ___.",
    )  # type: ignore[assignment]
    "Color: Color for the ___."

    final_gradient_stops: tuple[tte.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(tte.Color("8A008A"), tte.Color("00D1FF"), tte.Color("FFFFFF")),
        metavar=argvalidators.ColorArg.METAVAR,
        help=(
            "Space separated, unquoted, list of colors for the character gradient (applied across the canvas). "
            "If only one color is provided, the characters will be displayed in that color."
        ),
    )  # type: ignore[assignment]
    (
        "tuple[Color, ...]: Space separated, unquoted, list of colors for the character gradient "
        "(applied across the canvas). If only one color is provided, the characters will be displayed in that color."
    )

    final_gradient_steps: tuple[int, ...] | int = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argvalidators.PositiveInt.METAVAR,
        help=(
            "Space separated, unquoted, list of the number of gradient steps to use. More steps will "
            "create a smoother and longer gradient animation."
        ),
    )  # type: ignore[assignment]
    (
        "tuple[int, ...] | int: Space separated, unquoted, list of the number of gradient steps to use. More "
        "steps will create a smoother and longer gradient animation."
    )

    final_gradient_frames: int = ArgField(
        cmd_name="--final-gradient-frames",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=5,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step. Increase to slow down the gradient animation.",
    )  # type: ignore[assignment]
    "int: Number of frames to display each gradient step. Increase to slow down the gradient animation."

    final_gradient_direction: tte.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=tte.Gradient.Direction.VERTICAL,
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

    easing: tte.easing.EasingFunction = ArgField(
        cmd_name=["--easing"],
        default=tte.easing.in_out_sine,
        type_parser=argvalidators.Ease.type_parser,
        help="Easing function to use for character movement.",
    )  # type: ignore[assignment]
    "easing.EasingFunction: Easing function to use for character movement."

    @classmethod
    def get_effect_class(cls) -> type[Effect]:
        """Return the effect class associated with this configuration class."""
        return Effect


class EffectIterator(BaseEffectIterator[EffectConfig]):
    """Effect iterator for the NamedEffect effect."""

    def __init__(self, effect: Effect) -> None:
        """Initialize the effect iterator.

        Args:
            effect (NamedEffect): The effect to iterate over.

        """
        super().__init__(effect)
        self.pending_chars: list[tte.EffectCharacter] = []
        self.character_final_color_map: dict[tte.EffectCharacter, tte.Color] = {}
        self.build()

    def build(self) -> None:
        """Build the effect."""
        final_gradient = tte.Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
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
        """Return the next frame of the effect."""
        if self.pending_chars or self.active_characters:
            # perform effect logic
            self.update()
            return self.frame
        raise StopIteration


class Effect(BaseEffect[EffectConfig]):
    """Effect description."""

    @property
    def _config_cls(self) -> type[EffectConfig]:
        return EffectConfig

    @property
    def _iterator_cls(self) -> type[EffectIterator]:
        return EffectIterator
