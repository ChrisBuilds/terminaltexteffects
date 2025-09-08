"""Slide characters into view from outside the terminal.

Classes:
    Slide: Slide characters into view from outside the terminal.
    SlideConfig: Configuration for the Slide effect.
    SlideIterator: Effect iterator for the Slide effect. Does not normally need to be called directly.
"""

from __future__ import annotations

import typing
from dataclasses import dataclass

from terminaltexteffects import Color, EffectCharacter, Gradient, easing, geometry
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.argutils import ArgSpec, ParserSpec


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "slide", Slide, SlideConfig


@dataclass
class SlideConfig(BaseConfig):
    """Configuration for the Slide effect.

    Attributes:
        movement_speed (float): Speed of the characters. Valid values are n > 0.
        grouping (typing.Literal["row", "column", "diagonal"]): Direction to group characters. Valid values are
            'row', 'column', 'diagonal'.
        gap (int): Number of frames to wait before adding the next group of characters. Increasing this value
            creates a more staggered effect. Valid values are n >= 0.
        reverse_direction (bool): Reverse the direction of the characters.
        merge (bool): Merge the character groups originating.
        movement_easing (easing.EasingFunction): Easing function to use for character movement.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the character gradient. If only one color is
            provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps
            will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_frames (int): Number of frames to display each gradient step. Increase to slow down the
            gradient animation.
        final_gradient_direction (Gradient.Direction): Direction of the gradient.

    """

    parser_spec: ParserSpec = ParserSpec(
        name="slide",
        help="Slide characters into view from outside the terminal.",
        description=(
            "slide | Slide characters into view from outside the terminal, grouped by row, column, or diagonal."
        ),
        epilog=(
            f"{argutils.EASING_EPILOG} Example: terminaltexteffects slide --movement-speed 0.5 --grouping row "
            "--final-gradient-stops 833ab4 fd1d1d fcb045 --final-gradient-steps 12 --final-gradient-frames 10 "
            "--final-gradient-direction vertical --gap 3 --reverse-direction --merge --movement-easing OUT_QUAD"
        ),
    )

    movement_speed: float = ArgSpec(
        name="--movement-speed",
        type=argutils.PositiveFloat.type_parser,
        default=0.8,
        metavar=argutils.PositiveFloat.METAVAR,
        help="Speed of the characters.",
    )  # pyright: ignore[reportAssignmentType]
    "float : Speed of the characters."

    grouping: typing.Literal["row", "column", "diagonal"] = ArgSpec(
        name="--grouping",
        default="row",
        choices=["row", "column", "diagonal"],
        help="Direction to group characters.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "typing.Literal['row', 'column', 'diagonal'] : Direction to group characters. Valid values are "
        "Literal['row', 'column', 'diagonal']."
    )

    gap: int = ArgSpec(
        name="--gap",
        type=argutils.NonNegativeInt.type_parser,
        default=2,
        metavar=argutils.NonNegativeInt.METAVAR,
        help="Number of frames to wait before adding the next group of characters. Increasing this value creates a "
        "more staggered effect.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "int : Number of frames to wait before adding the next group of characters. Increasing this value creates a "
        "more staggered effect."
    )

    reverse_direction: bool = ArgSpec(
        name="--reverse-direction",
        default=False,
        action="store_true",
        help="Reverse the direction of the characters.",
    )  # pyright: ignore[reportAssignmentType]
    "bool : Reverse the direction of the characters."

    merge: bool = ArgSpec(
        name="--merge",
        default=False,
        action="store_true",
        help="Merge the character groups originating from either side of the terminal. (--reverse-direction is "
        "ignored when merging)",
    )  # pyright: ignore[reportAssignmentType]
    "bool : Merge the character groups originating from either side of the terminal."

    movement_easing: easing.EasingFunction = ArgSpec(
        name="--movement-easing",
        default=easing.in_out_quad,
        type=argutils.Ease.type_parser,
        metavar=argutils.Ease.METAVAR,
        help="Easing function to use for character movement.",
    )  # pyright: ignore[reportAssignmentType]
    "easing.EasingFunction : Easing function to use for character movement."

    final_gradient_stops: tuple[Color, ...] = ArgSpec(
        name="--final-gradient-stops",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        default=(Color("#833ab4"), Color("#fd1d1d"), Color("#fcb045")),
        metavar=argutils.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient. If only one color is provided, "
        "the characters will be displayed in that color.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[Color, ...] : Tuple of colors for the character gradient. If only one color is provided, the "
        "characters will be displayed in that color."
    )

    final_gradient_steps: tuple[int, ...] | int = ArgSpec(
        name="--final-gradient-steps",
        type=argutils.PositiveInt.type_parser,
        default=12,
        metavar=argutils.PositiveInt.METAVAR,
        help="Number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. More steps will "
        "create a smoother and longer gradient animation."
    )

    final_gradient_frames: int = ArgSpec(
        name="--final-gradient-frames",
        type=argutils.PositiveInt.type_parser,
        default=6,
        metavar=argutils.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step. Increase to slow down the gradient animation.",
    )  # pyright: ignore[reportAssignmentType]
    "int : Number of frames to display each gradient step. Increase to slow down the gradient animation."

    final_gradient_direction: Gradient.Direction = ArgSpec(
        name="--final-gradient-direction",
        default=Gradient.Direction.VERTICAL,
        type=argutils.GradientDirection.type_parser,
        help="Direction of the gradient (vertical, horizontal, diagonal, center).",
    )  # pyright: ignore[reportAssignmentType]
    "Gradient.Direction : Direction of the gradient."


class SlideIterator(BaseEffectIterator[SlideConfig]):
    """Effect iterator for the Slide effect."""

    def __init__(self, effect: Slide) -> None:
        """Initialize the Slide effect iterator."""
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.pending_groups: list[list[EffectCharacter]] = []
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.build()

    def build(self) -> None:  # noqa: PLR0915
        """Build the effect."""
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

        groups: list[list[EffectCharacter]] = []
        if self.config.grouping == "row":
            groups = self.terminal.get_characters_grouped(self.terminal.CharacterGroup.ROW_TOP_TO_BOTTOM)
        elif self.config.grouping == "column":
            groups = self.terminal.get_characters_grouped(self.terminal.CharacterGroup.COLUMN_LEFT_TO_RIGHT)
        elif self.config.grouping == "diagonal":
            groups = self.terminal.get_characters_grouped(
                self.terminal.CharacterGroup.DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT,
            )
        for group in groups:
            for character in group:
                input_path = character.motion.new_path(
                    path_id="input_path",
                    speed=self.config.movement_speed,
                    ease=self.config.movement_easing,
                )
                input_path.new_waypoint(character.input_coord)

        for group_index, group in enumerate(groups):
            if self.config.grouping == "row":
                if self.config.merge and group_index % 2 == 0:
                    starting_column = self.terminal.canvas.right + 1
                else:
                    groups[group_index] = groups[group_index][::-1]
                    starting_column = self.terminal.canvas.left - 1
                if self.config.reverse_direction and not self.config.merge:
                    groups[group_index] = groups[group_index][::-1]
                    starting_column = self.terminal.canvas.right + 1
                for character in groups[group_index]:
                    character.motion.set_coordinate(geometry.Coord(starting_column, character.input_coord.row))
            elif self.config.grouping == "column":
                if self.config.merge and group_index % 2 == 0:
                    starting_row = self.terminal.canvas.bottom - 1
                else:
                    groups[group_index] = groups[group_index][::-1]
                    starting_row = self.terminal.canvas.top + 1
                if self.config.reverse_direction and not self.config.merge:
                    groups[group_index] = groups[group_index][::-1]
                    starting_row = self.terminal.canvas.bottom - 1
                for character in groups[group_index]:
                    character.motion.set_coordinate(geometry.Coord(character.input_coord.column, starting_row))
            if self.config.grouping == "diagonal":
                distance_from_outside_bottom = group[-1].input_coord.row - (self.terminal.canvas.bottom - 1)
                starting_coord = geometry.Coord(
                    group[-1].input_coord.column - distance_from_outside_bottom,
                    group[-1].input_coord.row - distance_from_outside_bottom,
                )
                if self.config.merge and group_index % 2 == 0:
                    groups[group_index] = groups[group_index][::-1]
                    distance_from_outside = (self.terminal.canvas.top + 1) - group[0].input_coord.row
                    starting_coord = geometry.Coord(
                        group[0].input_coord.column + distance_from_outside,
                        group[0].input_coord.row + distance_from_outside,
                    )
                if self.config.reverse_direction and not self.config.merge:
                    groups[group_index] = groups[group_index][::-1]
                    distance_from_outside = (self.terminal.canvas.top + 1) - group[0].input_coord.row
                    starting_coord = geometry.Coord(
                        group[0].input_coord.column + distance_from_outside,
                        group[0].input_coord.row + distance_from_outside,
                    )

                for character in groups[group_index]:
                    character.motion.set_coordinate(starting_coord)
            for character in group:
                gradient_scn = character.animation.new_scene()
                char_gradient = Gradient(
                    self.config.final_gradient_stops[0],
                    self.character_final_color_map[character],
                    steps=10,
                )
                gradient_scn.apply_gradient_to_symbols(
                    character.input_symbol,
                    self.config.final_gradient_frames,
                    fg_gradient=char_gradient,
                )
                character.animation.activate_scene(gradient_scn)

        self.pending_groups = groups
        self._active_groups: list[list[EffectCharacter]] = []
        self._current_gap = 0

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        if self.pending_groups or self.active_characters or self._active_groups:
            if self._current_gap == self.config.gap and self.pending_groups:
                self._active_groups.append(self.pending_groups.pop(0))
                self._current_gap = 0
            elif self.pending_groups:
                self._current_gap += 1
            for group in self._active_groups:
                if group:
                    next_char = group.pop(0)
                    self.terminal.set_character_visibility(next_char, is_visible=True)
                    next_char.motion.activate_path(next_char.motion.paths["input_path"])
                    self.active_characters.add(next_char)
            self._active_groups = [group for group in self._active_groups if group]
            self.update()
            return self.frame
        raise StopIteration


class Slide(BaseEffect[SlideConfig]):
    """Slides characters into view from outside the terminal.

    Attributes:
        effect_config (SlideConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    @property
    def _config_cls(self) -> type[SlideConfig]:
        return SlideConfig

    @property
    def _iterator_cls(self) -> type[SlideIterator]:
        return SlideIterator
