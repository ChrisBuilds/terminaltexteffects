"""Effect Description.

Classes:

"""

from __future__ import annotations

import random
from dataclasses import dataclass

import terminaltexteffects as tte
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.argutils import ArgSpec, ParserSpec


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "sort", Effect, EffectConfig


@dataclass
class EffectConfig(BaseConfig):
    """Effect configuration dataclass."""

    parser_spec: ParserSpec = ParserSpec(
        name="sort",
        help="effect_description",
        description="effect_description",
        epilog=f"""{argutils.EASING_EPILOG}
    """,
    )

    color_single: tte.Color = ArgSpec(
        name="--color-single",
        type=argutils.ColorArg.type_parser,
        default=tte.Color(0),
        metavar=argutils.ColorArg.METAVAR,
        help="Color for the ___.",
    )  # pyright: ignore[reportAssignmentType]
    "Color: Color for the ___."

    final_gradient_stops: tuple[tte.Color, ...] = ArgSpec(
        name="--final-gradient-stops",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        default=(tte.Color("8A008A"), tte.Color("00D1FF"), tte.Color("FFFFFF")),
        metavar=argutils.ColorArg.METAVAR,
        help=(
            "Space separated, unquoted, list of colors for the character gradient (applied across the canvas). "
            "If only one color is provided, the characters will be displayed in that color."
        ),
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[Color, ...]: Space separated, unquoted, list of colors for the character gradient "
        "(applied across the canvas). If only one color is provided, the characters will be displayed in that color."
    )

    final_gradient_steps: tuple[int, ...] | int = ArgSpec(
        name="--final-gradient-steps",
        type=argutils.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argutils.PositiveInt.METAVAR,
        help=(
            "Space separated, unquoted, list of the number of gradient steps to use. More steps will "
            "create a smoother and longer gradient animation."
        ),
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[int, ...] | int: Space separated, unquoted, list of the number of gradient steps to use. More "
        "steps will create a smoother and longer gradient animation."
    )

    final_gradient_frames: int = ArgSpec(
        name="--final-gradient-frames",
        type=argutils.PositiveInt.type_parser,
        default=5,
        metavar=argutils.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step. Increase to slow down the gradient animation.",
    )  # pyright: ignore[reportAssignmentType]
    "int: Number of frames to display each gradient step. Increase to slow down the gradient animation."

    final_gradient_direction: tte.Gradient.Direction = ArgSpec(
        name="--final-gradient-direction",
        type=argutils.GradientDirection.type_parser,
        default=tte.Gradient.Direction.RADIAL,
        metavar=argutils.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # pyright: ignore[reportAssignmentType]
    "Gradient.Direction : Direction of the final gradient."

    movement_speed: float = ArgSpec(
        name="--movement-speed",
        type=argutils.PositiveFloat.type_parser,
        default=1,
        metavar=argutils.PositiveFloat.METAVAR,
        help="Speed of the ___.",
    )  # pyright: ignore[reportAssignmentType]
    "float: Speed of the ___."

    easing: tte.easing.EasingFunction = ArgSpec(
        name="--easing",
        default=tte.easing.in_out_sine,
        type=argutils.Ease.type_parser,
        help="Easing function to use for character movement.",
    )  # pyright: ignore[reportAssignmentType]
    "easing.EasingFunction: Easing function to use for character movement."


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
        self.rows_with_chars: set[int] = set()
        self.columns_with_chars: set[int] = set()
        self.character_path_waypoint_map: dict[tte.EffectCharacter, list[tte.Coord]] = {}
        self.opening_hold_time = 50
        self.path_ids: list[str] = []

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
            character.animation.set_appearance(colors=tte.ColorPair(fg=self.character_final_color_map[character]))
            self.rows_with_chars.add(character.input_coord.row)
            self.columns_with_chars.add(character.input_coord.column)
            self.character_path_waypoint_map[character] = [character.input_coord]
            self.terminal.set_character_visibility(character, is_visible=True)

        for _ in range(2):
            self.swap_rows(30)
            self.make_path_from_waypoints(path_id=str(len(self.path_ids)))
            self.swap_columns(30)
            self.make_path_from_waypoints(path_id=str(len(self.path_ids)))
        self.path_ids.reverse()

    def make_path_from_waypoints(self, path_id: str) -> None:
        self.path_ids.append(path_id)
        for character, waypoint_coords in self.character_path_waypoint_map.items():
            if len(waypoint_coords) == 1:
                continue
            return_path = character.motion.new_path(speed=0.7, path_id=path_id, layer=1, ease=tte.easing.out_sine)
            for coord in reversed(waypoint_coords):
                return_path.new_waypoint(coord)
            character.event_handler.register_event(
                event=tte.Event.PATH_COMPLETE,
                caller=return_path,
                action=tte.Action.SET_LAYER,
                target=0,
            )
            self.character_path_waypoint_map[character].clear()
            self.character_path_waypoint_map[character].append(character.motion.current_coord)

    def swap_columns(self, swaps: int) -> None:
        for _ in range(swaps):
            column_1 = random.choice(list(self.columns_with_chars))
            while (column_2 := random.choice(list(self.columns_with_chars))) == column_1:
                ...
            column_1_chars = [
                char for char in self.terminal.get_characters() if char.motion.current_coord.column == column_1
            ]
            column_2_chars = [
                char for char in self.terminal.get_characters() if char.motion.current_coord.column == column_2
            ]
            for char in column_1_chars:
                new_coord = tte.Coord(column_2, char.motion.current_coord.row)
                self.character_path_waypoint_map[char].append(
                    new_coord,
                )
                char.motion.set_coordinate(new_coord)
            for char in column_2_chars:
                new_coord = tte.Coord(column_1, char.motion.current_coord.row)
                self.character_path_waypoint_map[char].append(new_coord)
                char.motion.set_coordinate(new_coord)

    def swap_rows(self, swaps: int) -> None:
        for _ in range(swaps):
            row_1 = random.choice(list(self.rows_with_chars))
            while (row_2 := random.choice(list(self.rows_with_chars))) == row_1:
                ...
            row_1_chars = [char for char in self.terminal.get_characters() if char.motion.current_coord.row == row_1]
            row_2_chars = [char for char in self.terminal.get_characters() if char.motion.current_coord.row == row_2]
            for char in row_1_chars:
                new_coord = tte.Coord(char.motion.current_coord.column, row_2)
                self.character_path_waypoint_map[char].append(
                    new_coord,
                )
                char.motion.set_coordinate(new_coord)
            for char in row_2_chars:
                new_coord = tte.Coord(char.motion.current_coord.column, row_1)
                self.character_path_waypoint_map[char].append(new_coord)
                char.motion.set_coordinate(new_coord)

    def __next__(self) -> str:
        """Return the next frame of the effect."""
        if self.active_characters or self.path_ids:
            if self.opening_hold_time:
                self.opening_hold_time -= 1
            else:
                if not self.active_characters:
                    next_path_id = self.path_ids.pop(0)
                    for character in self.terminal.get_characters():
                        if path := character.motion.query_path(next_path_id, not_found_action=None):
                            character.motion.activate_path(path)
                            self.active_characters.add(character)
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
