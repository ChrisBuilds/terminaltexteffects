"""Slices the input in half vertically and slides it into place from opposite directions.

Classes:
    VerticalSlice: Slices the input in half vertically and slides it into place from opposite directions.
    VerticalSliceConfig: Configuration for the VerticalSlice effect.
    VerticalSliceIterator: Effect iterator for the effect. Does not normally need to be called directly.
"""

import typing
from dataclasses import dataclass

from terminaltexteffects.engine.base_character import EffectCharacter
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argvalidators, easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return VerticalSlice, VerticalSliceConfig


@argclass(
    name="verticalslice",
    help="Slices the input in half vertically and slides it into place from opposite directions.",
    description="verticalslice | Slices the input in half vertically and slides it into place from opposite directions.",
    epilog=f"""{argvalidators.EASING_EPILOG}
    
Example: terminaltexteffects verticalslice --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --movement-speed 0.15 --movement-easing IN_OUT_EXPO""",
)
@dataclass
class VerticalSliceConfig(ArgsDataClass):
    """Configuration for the VerticalSlice effect.

    Attributes:
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the final gradient.
        movement_speed (float): Movement speed of the characters. Valid values are n > 0.
        movement_easing (easing.EasingFunction): Easing function to use for character movement.
    """

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=("8A008A", "00D1FF", "FFFFFF"),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] : Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.VERTICAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "graphics.Gradient.Direction : Direction of the final gradient."

    movement_speed: float = ArgField(
        cmd_name="--movement-speed",
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=0.15,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Movement speed of the characters. ",
    )  # type: ignore[assignment]
    "float : Movement speed of the characters. "

    movement_easing: easing.EasingFunction = ArgField(
        cmd_name="--movement-easing",
        type_parser=argvalidators.Ease.type_parser,
        default=easing.in_out_expo,
        help="Easing function to use for character movement.",
    )  # type: ignore[assignment]
    "easing.EasingFunction : Easing function to use for character movement."

    @classmethod
    def get_effect_class(cls):
        return VerticalSlice


class VerticalSliceIterator(BaseEffectIterator[VerticalSliceConfig]):
    def __init__(self, effect: "VerticalSlice") -> None:
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.new_rows: list[list[EffectCharacter]] = []
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}
        self.build()

    def build(self) -> None:
        final_gradient = graphics.Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.config.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
            character.animation.set_appearance(
                character.input_symbol,
                self.character_final_color_map[character],
            )

        self.rows = self.terminal.get_characters_grouped(grouping=self.terminal.CharacterGroup.ROW_BOTTOM_TO_TOP)
        lengths = [max([c.input_coord.column for c in row]) for row in self.rows]
        mid_point = sum(lengths) // len(lengths) // 2
        for row_index, row in enumerate(self.rows):
            new_row = []
            left_half = [character for character in row if character.input_coord.column <= mid_point]
            for character in left_half:
                character.motion.set_coordinate(Coord(character.input_coord.column, self.terminal.output_area.top))
                input_coord_path = character.motion.new_path(
                    speed=self.config.movement_speed, ease=self.config.movement_easing
                )
                input_coord_path.new_waypoint(character.input_coord)
                character.motion.activate_path(input_coord_path)
            opposite_row = self.rows[-(row_index + 1)]
            right_half = [c for c in opposite_row if c.input_coord.column > mid_point]
            for character in right_half:
                character.motion.set_coordinate(Coord(character.input_coord.column, self.terminal.output_area.bottom))
                input_coord_path = character.motion.new_path(
                    speed=self.config.movement_speed, ease=self.config.movement_easing
                )
                input_coord_path.new_waypoint(character.input_coord)
                character.motion.activate_path(input_coord_path)
            new_row.extend(left_half)
            new_row.extend(right_half)
            self.new_rows.append(new_row)

    def __next__(self) -> str:
        if self.new_rows or self.active_characters:
            if self.new_rows:
                next_row = self.new_rows.pop(0)
                for character in next_row:
                    self.terminal.set_character_visibility(character, True)
                self.active_characters.extend(next_row)
            self.update()
            return self.frame
        else:
            raise StopIteration


class VerticalSlice(BaseEffect[VerticalSliceConfig]):
    """Slices the input in half vertically and slides it into place from opposite directions.

    Attributes:
        effect_config (VerticalSliceConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.
    """

    _config_cls = VerticalSliceConfig
    _iterator_cls = VerticalSliceIterator

    def __init__(self, input_data: str) -> None:
        """Initialize the effect with the provided input data.

        Args:
            input_data (str): The input data to use for the effect."""
        super().__init__(input_data)
