"""Slide characters into view from outside the terminal.

Classes:
    Slide: Slide characters into view from outside the terminal.
    SlideConfig: Configuration for the Slide effect.
    SlideIterator: Effect iterator for the Slide effect. Does not normally need to be called directly.
"""

import typing
from dataclasses import dataclass

import terminaltexteffects.utils.argvalidators as argvalidators
from terminaltexteffects.engine.base_character import EffectCharacter
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import easing, geometry, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return Slide, SlideConfig


@argclass(
    name="slide",
    help="Slide characters into view from outside the terminal.",
    description="slide | Slide characters into view from outside the terminal, grouped by row, column, or diagonal.",
    epilog=f"""{argvalidators.EASING_EPILOG}
Example: terminaltexteffects slide --movement-speed 0.5 --grouping row --final-gradient-stops 833ab4 fd1d1d fcb045 --final-gradient-steps 12 --final-gradient-frames 10 --final-gradient-direction vertical --gap 3 --reverse-direction --merge --movement-easing OUT_QUAD""",
)
@dataclass
class SlideConfig(ArgsDataClass):
    """Configuration for the Slide effect.

    Attributes:
        movement_speed (float): Speed of the characters. Valid values are n > 0.
        grouping (str): Direction to group characters. Valid values are 'row', 'column', 'diagonal'.
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the character gradient. If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_frames (int): Number of frames to display each gradient step.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the gradient.
        gap (int): Number of frames to wait before adding the next group of characters. Increasing this value creates a more staggered effect. Valid values are n >= 0.
        reverse_direction (bool): Reverse the direction of the characters.
        merge (bool): Merge the character groups originating"""

    movement_speed: float = ArgField(
        cmd_name="--movement-speed",
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=0.5,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Speed of the characters.",
    )  # type: ignore[assignment]
    "float : Speed of the characters."

    grouping: typing.Literal["row", "column", "diagonal"] = ArgField(
        cmd_name="--grouping",
        default="row",
        choices=["row", "column", "diagonal"],
        help="Direction to group characters.",
    )  # type: ignore[assignment]
    "str : Direction to group characters. Valid values are Literal['row', 'column', 'diagonal']."

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=("833ab4", "fd1d1d", "fcb045"),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient. If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the character gradient. If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=(12,),
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] : Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_frames: int = ArgField(
        cmd_name="--final-gradient-frames",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=10,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step.",
    )  # type: ignore[assignment]
    "int : Number of frames to display each gradient step."

    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        default=graphics.Gradient.Direction.VERTICAL,
        type_parser=argvalidators.GradientDirection.type_parser,
        help="Direction of the gradient (vertical, horizontal, diagonal, center).",
    )  # type: ignore[assignment]
    "graphics.Gradient.Direction : Direction of the gradient."

    gap: int = ArgField(
        cmd_name="--gap",
        type_parser=argvalidators.NonNegativeInt.type_parser,
        default=3,
        metavar=argvalidators.NonNegativeInt.METAVAR,
        help="Number of frames to wait before adding the next group of characters. Increasing this value creates a more staggered effect.",
    )  # type: ignore[assignment]
    "int : Number of frames to wait before adding the next group of characters. Increasing this value creates a more staggered effect."

    reverse_direction: bool = ArgField(
        cmd_name="--reverse-direction",
        action="store_true",
        help="Reverse the direction of the characters.",
    )  # type: ignore[assignment]
    "bool : Reverse the direction of the characters."

    merge: bool = ArgField(
        cmd_name="--merge",
        action="store_true",
        help="Merge the character groups originating from either side of the terminal. (--reverse-direction is ignored when merging)",
    )  # type: ignore[assignment]
    "bool : Merge the character groups originating from either side of the terminal."

    movement_easing: easing.EasingFunction = ArgField(
        cmd_name=["--movement-easing"],
        default=easing.in_out_quad,
        type_parser=argvalidators.Ease.type_parser,
        metavar=argvalidators.Ease.METAVAR,
        help="Easing function to use for character movement.",
    )  # type: ignore[assignment]
    "easing.EasingFunction : Easing function to use for character movement."

    @classmethod
    def get_effect_class(cls):
        return Slide


class SlideIterator(BaseEffectIterator[SlideConfig]):
    def __init__(self, effect: "Slide") -> None:
        super().__init__(effect)
        self._pending_chars: list[EffectCharacter] = []
        self._active_chars: list[EffectCharacter] = []
        self._pending_groups: list[list[EffectCharacter]] = []
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}
        self._build()

    def _build(self) -> None:
        final_gradient = graphics.Gradient(*self._config.final_gradient_stops, steps=self._config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self._terminal.output_area.top, self._terminal.output_area.right, self._config.final_gradient_direction
        )
        for character in self._terminal.get_characters():
            self._character_final_color_map[character] = final_gradient_mapping[character.input_coord]

        groups: list[list[EffectCharacter]] = []
        if self._config.grouping == "row":
            groups = self._terminal.get_characters_grouped(self._terminal.CharacterGroup.ROW_TOP_TO_BOTTOM)
        elif self._config.grouping == "column":
            groups = self._terminal.get_characters_grouped(self._terminal.CharacterGroup.COLUMN_LEFT_TO_RIGHT)
        elif self._config.grouping == "diagonal":
            groups = self._terminal.get_characters_grouped(
                self._terminal.CharacterGroup.DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT
            )
        for group in groups:
            for character in group:
                input_path = character.motion.new_path(
                    id="input_path", speed=self._config.movement_speed, ease=self._config.movement_easing
                )
                input_path.new_waypoint(character.input_coord)

        for group_index, group in enumerate(groups):
            if self._config.grouping == "row":
                if self._config.merge and group_index % 2 == 0:
                    starting_column = self._terminal.output_area.right + 1
                else:
                    groups[group_index] = groups[group_index][::-1]
                    starting_column = self._terminal.output_area.left - 1
                if self._config.reverse_direction and not self._config.merge:
                    groups[group_index] = groups[group_index][::-1]
                    starting_column = self._terminal.output_area.right + 1
                for character in groups[group_index]:
                    character.motion.set_coordinate(geometry.Coord(starting_column, character.input_coord.row))
            elif self._config.grouping == "column":
                if self._config.merge and group_index % 2 == 0:
                    starting_row = self._terminal.output_area.bottom - 1
                else:
                    groups[group_index] = groups[group_index][::-1]
                    starting_row = self._terminal.output_area.top + 1
                if self._config.reverse_direction and not self._config.merge:
                    groups[group_index] = groups[group_index][::-1]
                    starting_row = self._terminal.output_area.bottom - 1
                for character in groups[group_index]:
                    character.motion.set_coordinate(geometry.Coord(character.input_coord.column, starting_row))
            if self._config.grouping == "diagonal":
                distance_from_outside_bottom = group[-1].input_coord.row - (self._terminal.output_area.bottom - 1)
                starting_coord = geometry.Coord(
                    group[-1].input_coord.column - distance_from_outside_bottom,
                    group[-1].input_coord.row - distance_from_outside_bottom,
                )
                if self._config.merge and group_index % 2 == 0:
                    groups[group_index] = groups[group_index][::-1]
                    distance_from_outside = (self._terminal.output_area.top + 1) - group[0].input_coord.row
                    starting_coord = geometry.Coord(
                        group[0].input_coord.column + distance_from_outside,
                        group[0].input_coord.row + distance_from_outside,
                    )
                if self._config.reverse_direction and not self._config.merge:
                    groups[group_index] = groups[group_index][::-1]
                    distance_from_outside = (self._terminal.output_area.top + 1) - group[0].input_coord.row
                    starting_coord = geometry.Coord(
                        group[0].input_coord.column + distance_from_outside,
                        group[0].input_coord.row + distance_from_outside,
                    )

                for character in groups[group_index]:
                    character.motion.set_coordinate(starting_coord)
            for character in group:
                gradient_scn = character.animation.new_scene()
                char_gradient = graphics.Gradient(
                    self._config.final_gradient_stops[0], self._character_final_color_map[character], steps=10
                )
                gradient_scn.apply_gradient_to_symbols(
                    char_gradient, character.input_symbol, self._config.final_gradient_frames
                )
                character.animation.activate_scene(gradient_scn)

        self._pending_groups = groups
        self._active_groups: list[list[EffectCharacter]] = []
        self._current_gap = 0

    def __next__(self) -> str:
        if self._pending_groups or self._active_chars or self._active_groups:
            if self._current_gap == self._config.gap and self._pending_groups:
                self._active_groups.append(self._pending_groups.pop(0))
                self._current_gap = 0
            else:
                if self._pending_groups:
                    self._current_gap += 1
            for group in self._active_groups:
                if group:
                    next_char = group.pop(0)
                    self._terminal.set_character_visibility(next_char, True)
                    next_char.motion.activate_path(next_char.motion.paths["input_path"])
                    self._active_chars.append(next_char)
            self._active_groups = [group for group in self._active_groups if group]
            for character in self._active_chars:
                character.tick()
            self._active_chars = [character for character in self._active_chars if character.is_active]
            return self._terminal.get_formatted_output_string()
        else:
            raise StopIteration


class Slide(BaseEffect[SlideConfig]):
    """Slides characters into view from outside the terminal.

    Attributes:
        effect_config (SlideConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.
    """

    _config_cls = SlideConfig
    _iterator_cls = SlideIterator

    def __init__(self, input_data: str) -> None:
        """Initialize the effect with the provided input data.

        Args:
            input_data (str): The input data to use for the effect."""
        super().__init__(input_data)
