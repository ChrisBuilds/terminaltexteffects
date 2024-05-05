"""Performs a wipe across the terminal to reveal characters.

Classes:
    Wipe: Performs a wipe across the terminal to reveal characters.
    WipeConfig: Configuration for the Wipe effect.
    WipeIterator: Effect iterator for the Wipe effect. Does not normally need to be called directly.
"""

import typing
from dataclasses import dataclass

import terminaltexteffects.utils.argvalidators as argvalidators
from terminaltexteffects.engine.base_character import EffectCharacter
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return Wipe, WipeConfig


@argclass(
    name="wipe",
    help="Wipes the text across the terminal to reveal characters.",
    description="wipe | Wipes the text across the terminal to reveal characters.",
    epilog="""Example: terminaltexteffects wipe --wipe-direction diagonal_bottom_left_to_top_right --final-gradient-stops 833ab4 fd1d1d fcb045 --final-gradient-steps 12 --final-gradient-frames 5 --wipe-delay 0""",
)
@dataclass
class WipeConfig(ArgsDataClass):
    """Configuration for the Wipe effect.

    Attributes:
        wipe_direction (typing.Literal["column_left_to_right","row_top_to_bottom","row_bottom_to_top","diagonal_top_left_to_bottom_right","diagonal_bottom_left_to_top_right","diagonal_top_right_to_bottom_left","diagonal_bottom_right_to_top_left",]): Direction the text will wipe.
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the wipe gradient.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_frames (int): Number of frames to display each gradient step.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the final gradient.
        wipe_delay (int): Number of frames to wait before adding the next character group. Increase, to slow down the effect. Valid values are n >= 0."""

    wipe_direction: typing.Literal[
        "column_left_to_right",
        "row_top_to_bottom",
        "row_bottom_to_top",
        "diagonal_top_left_to_bottom_right",
        "diagonal_bottom_left_to_top_right",
        "diagonal_top_right_to_bottom_left",
        "diagonal_bottom_right_to_top_left",
    ] = ArgField(
        cmd_name="--wipe-direction",
        default="diagonal_bottom_left_to_top_right",
        choices=[
            "column_left_to_right",
            "column_right_to_left",
            "row_top_to_bottom",
            "row_bottom_to_top",
            "diagonal_top_left_to_bottom_right",
            "diagonal_bottom_left_to_top_right",
            "diagonal_top_right_to_bottom_left",
            "diagonal_bottom_right_to_top_left",
        ],
        help="Direction the text will wipe.",
    )  # type: ignore[assignment]
    "typing.Literal['column_left_to_right','row_top_to_bottom','row_bottom_to_top','diagonal_top_left_to_bottom_right','diagonal_bottom_left_to_top_right','diagonal_top_right_to_bottom_left','diagonal_bottom_right_to_top_left',] : Direction the text will wipe. Options: column_left_to_right, column_right_to_left, row_top_to_bottom, row_bottom_to_top, diagonal_top_left_to_bottom_right, diagonal_bottom_left_to_top_right, diagonal_top_right_to_bottom_left, diagonal_bottom_right_to_top_left."

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name="--final-gradient-stops",
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=("833ab4", "fd1d1d", "fcb045"),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the wipe gradient.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the wipe gradient."

    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] : Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_frames: int = ArgField(
        cmd_name="--final-gradient-frames",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=5,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step.",
    )  # type: ignore[assignment]
    "int : Number of frames to display each gradient step."

    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.VERTICAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "graphics.Gradient.Direction : Direction of the final gradient."

    wipe_delay: int = ArgField(
        cmd_name="--wipe-delay",
        type_parser=argvalidators.NonNegativeInt.type_parser,
        default=0,
        metavar=argvalidators.NonNegativeInt.METAVAR,
        help="Number of frames to wait before adding the next character group. Increase, to slow down the effect.",
    )  # type: ignore[assignment]
    "int : Number of frames to wait before adding the next character group. Increase, to slow down the effect."

    @classmethod
    def get_effect_class(cls):
        return Wipe


class WipeIterator(BaseEffectIterator[WipeConfig]):
    def __init__(self, effect: "Wipe") -> None:
        super().__init__(effect)
        self._pending_groups: list[list[EffectCharacter]] = []
        self._active_chars: list[EffectCharacter] = []
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}
        self._build()

    def _build(self) -> None:
        direction = self._config.wipe_direction
        final_gradient = graphics.Gradient(*self._config.final_gradient_stops, steps=self._config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self._terminal.output_area.top, self._terminal.output_area.right, self._config.final_gradient_direction
        )
        for character in self._terminal.get_characters():
            self._character_final_color_map[character] = final_gradient_mapping[character.input_coord]
        sort_map = {
            "column_left_to_right": self._terminal.CharacterGroup.COLUMN_LEFT_TO_RIGHT,
            "column_right_to_left": self._terminal.CharacterGroup.COLUMN_RIGHT_TO_LEFT,
            "row_top_to_bottom": self._terminal.CharacterGroup.ROW_TOP_TO_BOTTOM,
            "row_bottom_to_top": self._terminal.CharacterGroup.ROW_BOTTOM_TO_TOP,
            "diagonal_top_left_to_bottom_right": self._terminal.CharacterGroup.DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT,
            "diagonal_bottom_left_to_top_right": self._terminal.CharacterGroup.DIAGONAL_BOTTOM_LEFT_TO_TOP_RIGHT,
            "diagonal_top_right_to_bottom_left": self._terminal.CharacterGroup.DIAGONAL_TOP_RIGHT_TO_BOTTOM_LEFT,
            "diagonal_bottom_right_to_top_left": self._terminal.CharacterGroup.DIAGONAL_BOTTOM_RIGHT_TO_TOP_LEFT,
        }
        for group in self._terminal.get_characters_grouped(sort_map[direction]):
            for character in group:
                wipe_scn = character.animation.new_scene()
                wipe_gradient = graphics.Gradient(
                    final_gradient.spectrum[0],
                    self._character_final_color_map[character],
                    steps=self._config.final_gradient_steps,
                )
                wipe_scn.apply_gradient_to_symbols(
                    wipe_gradient, character.input_symbol, self._config.final_gradient_frames
                )
                character.animation.activate_scene(wipe_scn)
            self._pending_groups.append(group)
        self._wipe_delay = self._config.wipe_delay

    def __next__(self) -> str:
        if self._pending_groups or self._active_chars:
            if not self._wipe_delay:
                if self._pending_groups:
                    next_group = self._pending_groups.pop(0)
                    for character in next_group:
                        self._terminal.set_character_visibility(character, True)
                        self._active_chars.append(character)
                self._wipe_delay = self._config.wipe_delay
            else:
                self._wipe_delay -= 1
            for character in self._active_chars:
                character.tick()
            self._active_chars = [character for character in self._active_chars if character.is_active]
            return self._terminal.get_formatted_output_string()
        else:
            raise StopIteration


class Wipe(BaseEffect[WipeConfig]):
    """Performs a wipe across the terminal to reveal characters.

    Attributes:
        effect_config (WipeConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.
    """

    _config_cls = WipeConfig
    _iterator_cls = WipeIterator

    def __init__(self, input_data: str) -> None:
        """Initialize the effect with the provided input data.

        Args:
            input_data (str): The input data to use for the effect."""
        super().__init__(input_data)
