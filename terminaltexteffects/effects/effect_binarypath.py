"""
Decodes characters into their binary form. Characters travel from outside the output area towards their input coordinate, moving at right angles.

Classes:
    BinaryPath: Decodes characters into their binary form. Characters travel from outside the output area towards their input coordinate, moving at right angles.
    BinaryPathConfig: Configuration for the BinaryPath effect.
    BinaryPathIterator: Effect iterator for the BinaryPath effect. Does not normally need to be called directly.

"""

import random
import typing
from dataclasses import dataclass

import terminaltexteffects.utils.argvalidators as argvalidators
from terminaltexteffects.engine.base_character import EffectCharacter
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.terminal import Terminal
from terminaltexteffects.utils import easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return BinaryPath, BinaryPathConfig


@argclass(
    name="binarypath",
    help="Binary representations of each character move through the terminal towards the home coordinate of the character.",
    description="binarypath | Binary representations of each character move through the terminal towards the home coordinate of the character.",
    epilog="""Example: terminaltexteffects binarypath --final-gradient-stops 00d500 007500 --final-gradient-steps 12 --final-gradient-direction vertical --binary-colors 044E29 157e38 45bf55 95ed87 --movement-speed 1.0 --active-binary-groups 0.05""",
)
@dataclass
class BinaryPathConfig(ArgsDataClass):
    """Configuration for the BinaryPath effect.

    Attributes:
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the final gradient.
        binary_colors (tuple[graphics.Color, ...]): Tuple of colors for the binary characters. Character color is randomly assigned from this list.
        movement_speed (float): Speed of the binary groups as they travel around the terminal. Valid values are n > 0.
        active_binary_groups (float): Maximum number of binary groups that are active at any given time as a percentage of the total number of binary groups. Lower this to improve performance. Valid values are 0 < n <= 1."""

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=("00d500", "007500"),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]

    "tuple[graphics.Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name=["--final-gradient-steps"],
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]

    "tuple[int, ...] : Tuple of the number (n > 0) of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.CENTER,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]

    "graphics.Gradient.Direction : Direction of the final gradient."

    binary_colors: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--binary-colors"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=("044E29", "157e38", "45bf55", "95ed87"),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the binary characters. Character color is randomly assigned from this list.",
    )  # type: ignore[assignment]

    "tuple[graphics.Color, ...] : Tuple of colors for the binary characters. Character color is randomly assigned from this list."

    movement_speed: float = ArgField(
        cmd_name="--movement-speed",
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=1.0,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Speed of the binary groups as they travel around the terminal.",
    )  # type: ignore[assignment]

    "float : Speed of the binary groups as they travel around the terminal."

    active_binary_groups: float = ArgField(
        cmd_name="--active-binary-groups",
        type_parser=argvalidators.Ratio.type_parser,
        default=0.05,
        metavar=argvalidators.Ratio.METAVAR,
        help="Maximum number of binary groups that are active at any given time as a percentage of the total number of binary groups. Lower this to improve performance.",
    )  # type: ignore[assignment]

    "float : Maximum number of binary groups that are active at any given time as a percentage of the total number of binary groups. Lower this to improve performance."

    @classmethod
    def get_effect_class(cls):
        return BinaryPath


class BinaryPathIterator(BaseEffectIterator[BinaryPathConfig]):
    class _BinaryRepresentation:
        def __init__(self, character: EffectCharacter, terminal: Terminal):
            self.character = character
            self.terminal = terminal
            self.binary_string = format(ord(self.character.symbol), "08b")
            self.binary_characters: list[EffectCharacter] = []
            self.pending_binary_characters: list[EffectCharacter] = []
            self.input_coord = self.character.input_coord
            self.is_active = False

        def _travel_complete(self) -> bool:
            return all(bin_char.motion.current_coord == self.input_coord for bin_char in self.binary_characters)

        def _deactivate(self) -> None:
            for bin_char in self.binary_characters:
                self.terminal.set_character_visibility(bin_char, False)
            self.is_active = False

        def _activate_source_character(self) -> None:
            self.terminal.set_character_visibility(self.character, True)
            self.character.animation.activate_scene(self.character.animation.query_scene("collapse_scn"))

    def __init__(self, effect: "BinaryPath") -> None:
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.pending_binary_representations: list[BinaryPathIterator._BinaryRepresentation] = []
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}
        self.last_frame_provided = False
        self.active_binary_reps: list[BinaryPathIterator._BinaryRepresentation] = []
        self.complete = False
        self.phase = "travel"
        self.final_wipe_chars = self.terminal.get_characters_grouped(
            grouping=self.terminal.CharacterGroup.DIAGONAL_TOP_RIGHT_TO_BOTTOM_LEFT
        )
        self.max_active_binary_groups: int = 0
        self.build()

    def build(self) -> None:
        final_gradient = graphics.Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.config.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]

        for character in self.terminal.get_characters():
            bin_rep = BinaryPathIterator._BinaryRepresentation(character, self.terminal)
            for binary_char in bin_rep.binary_string:
                bin_rep.binary_characters.append(self.terminal.add_character(binary_char, Coord(0, 0)))
                bin_rep.pending_binary_characters.append(bin_rep.binary_characters[-1])
            self.pending_binary_representations.append(bin_rep)

        for bin_rep in self.pending_binary_representations:
            path_coords: list[Coord] = []
            starting_coord = self.terminal.output_area.random_coord(outside_scope=True)
            path_coords.append(starting_coord)
            last_orientation = random.choice(("col", "row"))
            while path_coords[-1] != bin_rep.character.input_coord:
                last_coord = path_coords[-1]
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
                    next_coord = Coord(
                        last_coord.column,
                        last_coord.row
                        + (
                            random.randint(1, min(max_row_distance, max(10, int(self.terminal._input_width * 0.2))))
                            * row_direction
                        ),
                    )
                    last_orientation = "row"
                elif last_orientation == "row" and max_column_distance > 0:
                    next_coord = Coord(
                        last_coord.column + (random.randint(1, min(max_column_distance, 4)) * column_direction),
                        last_coord.row,
                    )
                    last_orientation = "col"
                else:
                    next_coord = bin_rep.character.input_coord

                path_coords.append(next_coord)

            path_coords.append(next_coord)
            final_coord = bin_rep.character.input_coord
            path_coords.append(final_coord)
            for bin_effectchar in bin_rep.binary_characters:
                bin_effectchar.motion.set_coordinate(path_coords[0])
                digital_path = bin_effectchar.motion.new_path(speed=self.config.movement_speed)
                for coord in path_coords:
                    digital_path.new_waypoint(coord)
                bin_effectchar.motion.activate_path(digital_path)
                bin_effectchar.layer = 1
                color_scn = bin_effectchar.animation.new_scene()
                color_scn.add_frame(bin_effectchar.symbol, 1, color=random.choice(self.config.binary_colors))
                bin_effectchar.animation.activate_scene(color_scn)

        for character in self.terminal.get_characters():
            collapse_scn = character.animation.new_scene(ease=easing.in_quad, id="collapse_scn")
            dim_color = character.animation.adjust_color_brightness(self.character_final_color_map[character], 0.5)
            dim_gradient = graphics.Gradient("ffffff", dim_color, steps=10)
            collapse_scn.apply_gradient_to_symbols(dim_gradient, character.input_symbol, 7)

            brighten_scn = character.animation.new_scene(id="brighten_scn")
            brighten_gradient = graphics.Gradient(dim_color, self.character_final_color_map[character], steps=10)
            brighten_scn.apply_gradient_to_symbols(brighten_gradient, character.input_symbol, 2)
        self.max_active_binary_groups = max(
            1, int(self.config.active_binary_groups * len(self.pending_binary_representations))
        )

    def __next__(self) -> str:
        if not self.complete or self.active_characters:
            if self.phase == "travel":
                while (
                    len(self.active_binary_reps) < self.max_active_binary_groups and self.pending_binary_representations
                ):
                    next_binary_rep = self.pending_binary_representations.pop(
                        random.randrange(len(self.pending_binary_representations))
                    )
                    next_binary_rep.is_active = True
                    self.active_binary_reps.append(next_binary_rep)

                if self.active_binary_reps:
                    for active_rep in self.active_binary_reps:
                        if active_rep.pending_binary_characters:
                            next_char = active_rep.pending_binary_characters.pop(0)
                            self.active_characters.append(next_char)
                            self.terminal.set_character_visibility(next_char, True)
                        elif active_rep._travel_complete():
                            active_rep._deactivate()
                            active_rep._activate_source_character()
                            self.active_characters.append(active_rep.character)

                    self.active_binary_reps = [
                        binary_rep for binary_rep in self.active_binary_reps if binary_rep.is_active
                    ]

                if not self.active_characters:
                    self.phase = "wipe"

            if self.phase == "wipe":
                if self.final_wipe_chars:
                    next_group = self.final_wipe_chars.pop(0)
                    for character in next_group:
                        character.animation.activate_scene(character.animation.query_scene("brighten_scn"))
                        self.terminal.set_character_visibility(character, True)
                        self.active_characters.append(character)
                else:
                    self.complete = True

            self.update()
            return self.frame

        elif not self.last_frame_provided:
            self.last_frame_provided = True
            return self.frame

        else:
            raise StopIteration


class BinaryPath(BaseEffect):
    """Decodes characters into their binary form. Characters travel from outside the output area towards their input coordinate, moving at right angles.

    Attributes:
        effect_config (BinaryPathConfig): Configuration for the BinaryPath effect.
        terminal_config (TerminalConfig): Configuration for the terminal.


    """

    _config_cls = BinaryPathConfig
    _iterator_cls = BinaryPathIterator

    def __init__(self, input_data: str) -> None:
        """Initializes the BinaryPath effect with the provided input data.

        Args:
            input_data (str): The input data to use for the BinaryPath effect."""
        super().__init__(input_data)
