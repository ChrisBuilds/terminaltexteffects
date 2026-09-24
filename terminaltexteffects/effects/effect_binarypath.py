"""Encodes characters as binary and routes the bits from outside the canvas to their input coordinates.

Classes:
    `BinaryPath`: Encodes characters as binary and moves the bits from outside the canvas toward their input
        coordinates along right-angle paths.
    `BinaryPathConfig`: Configuration for the BinaryPath effect.
    `BinaryPathIterator`: Effect iterator for the BinaryPath effect. Does not normally need to be called directly.

"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import cast

import terminaltexteffects as tte
from terminaltexteffects.engine.base_config import (
    BaseConfig,
    FinalGradientDirectionArg,
    FinalGradientStopsArg,
)
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "binarypath", BinaryPath, BinaryPathConfig


@dataclass
class BinaryPathConfig(BaseConfig):
    """Configuration for the BinaryPath effect.

    Attributes:
        final_gradient_stops (tuple[tte.Color, ...]): Tuple of colors for the final color gradient. If only one color
            is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Number of color transitions in the spatial final-color gradient.
            More steps create smoother color transitions. Valid values are n > 0.
        final_gradient_direction (tte.Gradient.Direction): Direction of the final gradient.
        binary_colors (tuple[tte.Color, ...]): Tuple of colors for the binary characters. Character color is randomly
            assigned from this list.
        movement_speed (float): Speed of the binary groups along right-angle paths from outside the canvas toward
            their input coordinates. Valid values are n > 0.
        active_binary_groups (float): Maximum fraction of binary groups active at once. Valid values are 0 <= n <= 1.
            A value of 0 still activates one group because the iterator enforces a one-group minimum.

    """

    parser_spec: argutils.ParserSpec = argutils.ParserSpec(
        name="binarypath",
        help="Characters are encoded as binary and move from outside the canvas toward their input coordinates.",
        description="binarypath | Characters are encoded as binary and move from outside the canvas toward their "
        "input coordinates along right-angle paths.",
        epilog=(
            "Example: terminaltexteffects binarypath --final-gradient-stops 00d500 007500 --final-gradient-steps 12 "
            "--final-gradient-direction radial --binary-colors 044E29 157e38 45bf55 95ed87 --movement-speed 1 "
            "--active-binary-groups 0.08"
        ),
    )

    final_gradient_stops: tuple[tte.Color, ...] = FinalGradientStopsArg(
        default=(tte.Color("#00d500"), tte.Color("#007500")),
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[tte.Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, "
        "the characters will be displayed in that color."
    )

    final_gradient_steps: tuple[int, ...] | int = argutils.ArgSpec(
        name="--final-gradient-steps",
        type=argutils.PositiveInt.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=12,
        metavar=argutils.PositiveInt.METAVAR,
        help="Number of color-transition steps used for the spatial final-color gradient.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[int, ...] | int : Number of color-transition steps used to create the spatial final-color gradient. "
        "More steps create smoother color transitions. Valid values are n > 0."
    )

    final_gradient_direction: tte.Gradient.Direction = FinalGradientDirectionArg(
        default=tte.Gradient.Direction.RADIAL,
    )  # pyright: ignore[reportAssignmentType]
    "tte.Gradient.Direction : Direction of the final gradient."

    binary_colors: tuple[tte.Color, ...] = argutils.ArgSpec(
        name="--binary-colors",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=(tte.Color("#044E29"), tte.Color("#157e38"), tte.Color("#45bf55"), tte.Color("#95ed87")),
        metavar=argutils.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the binary characters. Character color is randomly "
        "assigned from this list.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[tte.Color, ...] : Tuple of colors for the binary characters. Character color is randomly assigned from "
        "this list."
    )

    movement_speed: float = argutils.ArgSpec(
        name="--movement-speed",
        type=argutils.PositiveFloat.type_parser,
        default=1,
        metavar=argutils.PositiveFloat.METAVAR,
        help="Speed of the binary groups along right-angle paths from outside the canvas toward their input "
        "coordinates.",
    )  # pyright: ignore[reportAssignmentType]
    "float : Speed of the binary groups along right-angle paths from outside the canvas toward their input coordinates."

    active_binary_groups: float = argutils.ArgSpec(
        name="--active-binary-groups",
        type=argutils.NonNegativeRatio.type_parser,
        default=0.08,
        metavar=argutils.NonNegativeRatio.METAVAR,
        help="Maximum fraction of binary groups active at once. Values range from 0 to 1; 0 still activates one group.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "float : Maximum fraction of binary groups active at once. Values range from 0 to 1; 0 still activates one "
        "group because the iterator enforces a one-group minimum."
    )


class BinaryPathIterator(BaseEffectIterator[BinaryPathConfig]):
    """Iterator for the BinaryPath effect."""

    class _BinaryRepresentation:
        """Binary representation of a character. Used to animate the characters moving towards the input coordinate."""

        def __init__(self, character: tte.EffectCharacter, terminal: tte.Terminal) -> None:
            self.character = character
            self.terminal = terminal
            self.binary_string = format(ord(self.character.animation.current_character_visual.symbol), "08b")
            self.binary_characters: list[tte.EffectCharacter] = []
            self.pending_binary_characters: list[tte.EffectCharacter] = []
            self.input_coord = self.character.input_coord
            self.is_active = False

        def _travel_complete(self) -> bool:
            return all(bin_char.motion.current_coord == self.input_coord for bin_char in self.binary_characters)

        def _deactivate(self) -> None:
            for bin_char in self.binary_characters:
                self.terminal.set_character_visibility(bin_char, is_visible=False)
            self.is_active = False

        def _activate_source_character(self) -> None:
            self.terminal.set_character_visibility(self.character, is_visible=True)
            self.character.animation.activate_scene("collapse_scn")

    def __init__(self, effect: BinaryPath) -> None:
        """Initialize the BinaryPath effect iterator.

        Args:
            effect (BinaryPath): The BinaryPath effect instance.

        """
        super().__init__(effect)
        self.pending_binary_representations: list[BinaryPathIterator._BinaryRepresentation] = []
        self.last_frame_provided = False
        self.active_binary_reps: list[BinaryPathIterator._BinaryRepresentation] = []
        self.complete = False
        self.phase = "travel"
        self.final_wipe_chars = self.terminal.get_characters_grouped(
            grouping=argutils.CharacterGroup.DIAGONAL_TOP_RIGHT_TO_BOTTOM_LEFT,
        )
        self.max_active_binary_groups: int = 0
        self.build()

    def build(self) -> None:  # noqa: PLR0915
        """Build the BinaryPath effect."""
        final_gradient = tte.Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.text_bottom,
            self.terminal.canvas.text_top,
            self.terminal.canvas.text_left,
            self.terminal.canvas.text_right,
            self.config.final_gradient_direction,
        )
        for character in self.terminal.get_characters():
            bin_rep = BinaryPathIterator._BinaryRepresentation(character, self.terminal)
            for binary_char in bin_rep.binary_string:
                bin_rep.binary_characters.append(self.terminal.add_character(binary_char, tte.Coord(0, 0)))
                bin_rep.pending_binary_characters.append(bin_rep.binary_characters[-1])
            self.pending_binary_representations.append(bin_rep)

        for bin_rep in self.pending_binary_representations:
            starting_coord = self.terminal.canvas.random_coord(outside_scope=True)
            last_coord = starting_coord
            path_waypoints: list[tte.Coord] = []
            last_orientation = random.choice(("col", "row"))
            while last_coord != bin_rep.character.input_coord:
                if last_coord.column > bin_rep.character.input_coord.column:
                    column_direction = -1
                elif last_coord.column == bin_rep.character.input_coord.column:
                    column_direction = 0
                else:
                    column_direction = 1
                if last_coord.row > bin_rep.character.input_coord.row:
                    row_direction = -1
                elif last_coord.row == bin_rep.character.input_coord.row:
                    row_direction = 0
                else:
                    row_direction = 1
                max_column_distance = abs(last_coord.column - bin_rep.character.input_coord.column)
                max_row_distance = abs(last_coord.row - bin_rep.character.input_coord.row)
                if last_orientation == "col" and max_row_distance > 0:
                    next_coord = tte.Coord(
                        last_coord.column,
                        last_coord.row
                        + (
                            random.randint(1, min(max_row_distance, max(10, int(self.terminal.canvas.right * 0.2))))
                            * row_direction
                        ),
                    )
                    last_orientation = "row"
                elif last_orientation == "row" and max_column_distance > 0:
                    next_coord = tte.Coord(
                        last_coord.column + (random.randint(1, min(max_column_distance, 4)) * column_direction),
                        last_coord.row,
                    )
                    last_orientation = "col"
                else:
                    next_coord = bin_rep.character.input_coord

                path_waypoints.append(next_coord)
                last_coord = next_coord

            for bin_effectchar in bin_rep.binary_characters:
                bin_effectchar.motion.set_coordinate(starting_coord)
                digital_path = bin_effectchar.motion.new_path(speed=self.config.movement_speed)
                for coord in path_waypoints:
                    digital_path.new_waypoint(coord)
                bin_effectchar.motion.activate_path(digital_path)
                bin_effectchar.layer = 1
                bin_effectchar.animation.set_appearance(colors=tte.ColorPair(fg=random.choice(self.config.binary_colors)))

        for character in self.terminal.get_characters():
            collapse_scn = character.animation.new_scene(ease=tte.easing.in_quad, scene_id="collapse_scn")
            if self.terminal.config.existing_color_handling == "dynamic":
                final_fg_color = character.animation.input_fg_color
                final_bg_color = character.animation.input_bg_color
            else:
                final_fg_color = final_gradient_mapping[character.input_coord]
                final_bg_color = None
            dim_fg_color = (
                character.animation.adjust_color_brightness(final_fg_color, 0.5)
                if final_fg_color
                else None
            )
            dim_bg_color = (
                character.animation.adjust_color_brightness(final_bg_color, 0.5)
                if final_bg_color
                else None
            )
            collapse_fg_gradient = tte.Gradient(tte.Color("#ffffff"), dim_fg_color, steps=7) if dim_fg_color else None
            collapse_bg_gradient = tte.Gradient(tte.Color("#ffffff"), dim_bg_color, steps=7) if dim_bg_color else None
            if collapse_fg_gradient or collapse_bg_gradient:
                collapse_scn.apply_gradient_to_symbols(
                    character.input_symbol,
                    3,
                    fg_gradient=collapse_fg_gradient,
                    bg_gradient=collapse_bg_gradient,
                )
            else:
                collapse_scn.add_frame(character.input_symbol, 3, colors=tte.ColorPair())

            brighten_scn = character.animation.new_scene(scene_id="brighten_scn")
            brighten_fg_gradient = (
                tte.Gradient(dim_fg_color, cast("tte.Color", final_fg_color), steps=10) if dim_fg_color else None
            )
            brighten_bg_gradient = (
                tte.Gradient(dim_bg_color, cast("tte.Color", final_bg_color), steps=10) if dim_bg_color else None
            )
            if brighten_fg_gradient or brighten_bg_gradient:
                brighten_scn.apply_gradient_to_symbols(
                    character.input_symbol,
                    2,
                    fg_gradient=brighten_fg_gradient,
                    bg_gradient=brighten_bg_gradient,
                )
            else:
                brighten_scn.add_frame(character.input_symbol, 2, colors=tte.ColorPair())
        self.max_active_binary_groups = max(
            1,
            int(self.config.active_binary_groups * len(self.pending_binary_representations)),
        )

    def __next__(self) -> str:
        """Return the next frame in the effect."""
        if not self.complete or self.active_characters:
            if self.phase == "travel":
                while (
                    len(self.active_binary_reps) < self.max_active_binary_groups and self.pending_binary_representations
                ):
                    next_binary_rep = self.pending_binary_representations.pop(
                        random.randrange(len(self.pending_binary_representations)),
                    )
                    next_binary_rep.is_active = True
                    self.active_binary_reps.append(next_binary_rep)

                if self.active_binary_reps:
                    for active_rep in self.active_binary_reps:
                        if active_rep.pending_binary_characters:
                            next_char = active_rep.pending_binary_characters.pop(0)
                            self.active_characters.add(next_char)
                            self.terminal.set_character_visibility(next_char, is_visible=True)
                        elif active_rep._travel_complete():
                            active_rep._deactivate()
                            active_rep._activate_source_character()
                            self.active_characters.add(active_rep.character)

                    self.active_binary_reps = [
                        binary_rep for binary_rep in self.active_binary_reps if binary_rep.is_active
                    ]

                if not self.active_characters:
                    self.phase = "wipe"

            if self.phase == "wipe":
                for _ in range(2):
                    if self.final_wipe_chars:
                        next_group = self.final_wipe_chars.pop(0)
                        for character in next_group:
                            character.animation.activate_scene("brighten_scn")
                            self.terminal.set_character_visibility(character, is_visible=True)
                            self.active_characters.add(character)
                    else:
                        self.complete = True

            self.update()
            return self.frame

        if not self.last_frame_provided:
            self.last_frame_provided = True
            return self.frame

        raise StopIteration


class BinaryPath(BaseEffect):
    """Decode characters into their binary form. Characters travel to their input coordinate, moving at right angles.

    Attributes:
        effect_config (BinaryPathConfig): Configuration for the BinaryPath effect.
        terminal_config (TerminalConfig): Configuration for the terminal.


    """

    @property
    def _config_cls(self) -> type[BinaryPathConfig]:
        return BinaryPathConfig

    @property
    def _iterator_cls(self) -> type[BinaryPathIterator]:
        return BinaryPathIterator
