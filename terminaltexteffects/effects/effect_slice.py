"""Slices the input in half and slides it into place from opposite directions.

Classes:
    Slice: Slices the input in half and slides it into place from opposite directions.
    SliceConfig: Configuration for the Slice effect.
    SliceIterator: Effect iterator for the effect. Does not normally need to be called directly.
"""

import typing
from dataclasses import dataclass

from terminaltexteffects.engine.base_character import EffectCharacter
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argvalidators, easing
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.graphics import Color, Gradient


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return Slice, SliceConfig


@argclass(
    name="slice",
    help="Slices the input in half and slides it into place from opposite directions.",
    description="slice | Slices the input in half and slides it into place from opposite directions.",
    epilog=f"""{argvalidators.EASING_EPILOG}
    
Example: terminaltexteffects slice --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12
--slice-direction vertical--movement-speed 0.15 --movement-easing IN_OUT_EXPO""",
)
@dataclass
class SliceConfig(ArgsDataClass):
    """Configuration for the Slice effect.

    Attributes:
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.
        slice_direction (typing.Literal["vertical", "horizontal", "diagonal"]): Direction of the slice.
        movement_speed (float): Movement speed of the characters. Valid values are n > 0.
        movement_easing (easing.EasingFunction): Easing function to use for character movement.
    """

    final_gradient_stops: tuple[Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("8A008A"), Color("00D1FF"), Color("FFFFFF")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] | int = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_direction: Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=Gradient.Direction.DIAGONAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "Gradient.Direction : Direction of the final gradient."

    slice_direction: typing.Literal["vertical", "horizontal", "diagonal"] = ArgField(
        cmd_name="--slice-direction",
        default="vertical",
        choices=["vertical", "horizontal", "diagonal"],
        help="Direction of the slice.",
    )  # type: ignore[assignment]
    "typing.Literal['vertical', 'horizontal', 'diagonal'] : Direction of the slice."

    movement_speed: float = ArgField(
        cmd_name="--movement-speed",
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=0.15,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Movement speed of the characters. ",
    )  # type: ignore[assignment]
    "float : Movement speed of the characters. Doubled for horizontal slices."

    movement_easing: easing.EasingFunction = ArgField(
        cmd_name="--movement-easing",
        type_parser=argvalidators.Ease.type_parser,
        default=easing.in_out_expo,
        help="Easing function to use for character movement.",
    )  # type: ignore[assignment]
    "easing.EasingFunction : Easing function to use for character movement."

    @classmethod
    def get_effect_class(cls):
        return Slice


class SliceIterator(BaseEffectIterator[SliceConfig]):
    def __init__(self, effect: "Slice") -> None:
        super().__init__(effect)
        self.pending_groups: list[list[EffectCharacter]] = []
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.build()

    def build(self) -> None:
        slice_direction_map = {
            "vertical": self.terminal.CharacterGroup.ROW_BOTTOM_TO_TOP,
            "horizontal": self.terminal.CharacterGroup.COLUMN_RIGHT_TO_LEFT,
            "diagonal": self.terminal.CharacterGroup.DIAGONAL_BOTTOM_LEFT_TO_TOP_RIGHT,
        }
        final_gradient = Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.top, self.terminal.canvas.right, self.config.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
            character.animation.set_appearance(
                character.input_symbol,
                self.character_final_color_map[character],
            )
        if self.config.slice_direction == "vertical":
            self.rows = self.terminal.get_characters_grouped(grouping=slice_direction_map[self.config.slice_direction])
            lengths = [max([c.input_coord.column for c in row]) for row in self.rows]
            mid_point = sum(lengths) // len(lengths) // 2
            for row_index, row in enumerate(self.rows):
                new_row = []

                left_half = [character for character in row if character.input_coord.column <= mid_point]
                for character in left_half:
                    character.motion.set_coordinate(Coord(character.input_coord.column, self.terminal.canvas.top + 1))
                    input_coord_path = character.motion.new_path(
                        speed=self.config.movement_speed, ease=self.config.movement_easing
                    )
                    input_coord_path.new_waypoint(character.input_coord)
                    character.motion.activate_path(input_coord_path)
                opposite_row = self.rows[-(row_index + 1)]
                right_half = [c for c in opposite_row if c.input_coord.column > mid_point]
                for character in right_half:
                    character.motion.set_coordinate(
                        Coord(character.input_coord.column, self.terminal.canvas.bottom - 1)
                    )
                    input_coord_path = character.motion.new_path(
                        speed=self.config.movement_speed, ease=self.config.movement_easing
                    )
                    input_coord_path.new_waypoint(character.input_coord)
                    character.motion.activate_path(input_coord_path)
                new_row.extend(left_half)
                new_row.extend(right_half)
                self.active_characters.extend(new_row)
        elif self.config.slice_direction == "horizontal":
            self.config.movement_speed *= 2
            self.columns = self.terminal.get_characters_grouped(
                grouping=slice_direction_map[self.config.slice_direction], fill_chars=True
            )
            lengths = [max([c.input_coord.row for c in column]) for column in self.columns]
            mid_point = sum(lengths) // len(lengths) // 2
            for column_index, column in enumerate(self.columns):
                new_column = []

                bottom_half = [character for character in column if character.input_coord.row <= mid_point]
                for character in bottom_half:
                    character.motion.set_coordinate(Coord(self.terminal.canvas.left - 1, character.input_coord.row))
                    input_coord_path = character.motion.new_path(
                        speed=self.config.movement_speed, ease=self.config.movement_easing
                    )
                    input_coord_path.new_waypoint(character.input_coord)
                    character.motion.activate_path(input_coord_path)
                opposite_column = self.columns[-(column_index + 1)]
                top_half = [c for c in opposite_column if c.input_coord.row > mid_point]
                for character in top_half:
                    character.motion.set_coordinate(Coord(self.terminal.canvas.right + 1, character.input_coord.row))
                    input_coord_path = character.motion.new_path(
                        speed=self.config.movement_speed, ease=self.config.movement_easing
                    )
                    input_coord_path.new_waypoint(character.input_coord)
                    character.motion.activate_path(input_coord_path)
                new_column.extend(bottom_half)
                new_column.extend(top_half)
                self.active_characters.extend(new_column)
        elif self.config.slice_direction == "diagonal":
            self.diagonals = self.terminal.get_characters_grouped(
                grouping=slice_direction_map[self.config.slice_direction]
            )
            left = self.diagonals[: len(self.diagonals) // 2]
            right = self.diagonals[len(self.diagonals) // 2 :]
            while left or right:
                new_group = []
                if left:
                    left_group = left.pop(0)
                    origin_coord = Coord(left_group[0].input_coord.column, self.terminal.canvas.bottom - 1)
                    for character in left_group:
                        character.motion.set_coordinate(origin_coord)
                        input_coord_path = character.motion.new_path(
                            speed=self.config.movement_speed, ease=self.config.movement_easing
                        )
                        input_coord_path.new_waypoint(character.input_coord)
                        character.motion.activate_path(input_coord_path)
                    new_group.extend(left_group)
                if right:
                    right_group = right.pop(0)
                    origin_coord = Coord(right_group[-1].input_coord.column, self.terminal.canvas.top + 1)
                    for character in right_group:
                        character.motion.set_coordinate(origin_coord)
                        input_coord_path = character.motion.new_path(
                            speed=self.config.movement_speed, ease=self.config.movement_easing
                        )
                        input_coord_path.new_waypoint(character.input_coord)
                        character.motion.activate_path(input_coord_path)
                    new_group.extend(right_group)
                self.active_characters.extend(new_group)
        for character in self.active_characters:
            self.terminal.set_character_visibility(character, True)

    def __next__(self) -> str:
        if self.active_characters:
            self.update()
            return self.frame
        else:
            raise StopIteration


class Slice(BaseEffect[SliceConfig]):
    """Slices the input in half and slides it into place from opposite directions.

    Attributes:
        effect_config (SliceConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.
    """

    _config_cls = SliceConfig
    _iterator_cls = SliceIterator

    def __init__(self, input_data: str) -> None:
        """Initialize the effect with the provided input data.

        Args:
            input_data (str): The input data to use for the effect."""
        super().__init__(input_data)
