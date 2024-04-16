import typing
from collections.abc import Iterator
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils import easing, geometry, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.terminal import Terminal, TerminalConfig


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return SlideEffect, EffectConfig


@argclass(
    name="slide",
    help="Slide characters into view from outside the terminal.",
    description="slide | Slide characters into view from outside the terminal, grouped by row, column, or diagonal.",
    epilog=f"""{arg_validators.EASING_EPILOG}
Example: terminaltexteffects slide --movement-speed 0.5 --grouping row --final-gradient-stops 833ab4 fd1d1d fcb045 --final-gradient-steps 12 --final-gradient-frames 10 --final-gradient-direction vertical --gap 3 --reverse-direction --merge --movement-easing OUT_QUAD""",
)
@dataclass
class EffectConfig(ArgsDataClass):
    """Configuration for the Slide effect.

    Attributes:
        movement_speed (float): Speed of the characters.
        grouping (str): Direction to group characters.
        final_gradient_stops (tuple[int | str, ...]): Tuple of colors for the character gradient. If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.
        final_gradient_frames (int): Number of frames to display each gradient step.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the gradient.
        gap (int): Number of frames to wait before adding the next group of characters. Increasing this value creates a more staggered effect.
        reverse_direction (bool): Reverse the direction of the characters.
        merge (bool): Merge the character groups originating"""

    movement_speed: float = ArgField(
        cmd_name="--movement-speed",
        type_parser=arg_validators.PositiveFloat.type_parser,
        default=0.5,
        metavar=arg_validators.PositiveFloat.METAVAR,
        help="Speed of the characters.",
    )  # type: ignore[assignment]
    "float : Speed of the characters."

    grouping: str = ArgField(
        cmd_name="--grouping",
        default="row",
        choices=["row", "column", "diagonal"],
        help="Direction to group characters.",
    )  # type: ignore[assignment]
    "str : Direction to group characters."

    final_gradient_stops: tuple[int | str, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("833ab4", "fd1d1d", "fcb045"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient. If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[int | str, ...] : Tuple of colors for the character gradient. If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=arg_validators.PositiveInt.type_parser,
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] : Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_frames: int = ArgField(
        cmd_name="--final-gradient-frames",
        type_parser=arg_validators.PositiveInt.type_parser,
        default=10,
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step.",
    )  # type: ignore[assignment]
    "int : Number of frames to display each gradient step."

    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        default=graphics.Gradient.Direction.VERTICAL,
        type_parser=arg_validators.GradientDirection.type_parser,
        help="Direction of the gradient (vertical, horizontal, diagonal, center).",
    )  # type: ignore[assignment]
    "graphics.Gradient.Direction : Direction of the gradient."

    gap: int = ArgField(
        cmd_name="--gap",
        type_parser=arg_validators.NonNegativeInt.type_parser,
        default=3,
        metavar=arg_validators.NonNegativeInt.METAVAR,
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
        type_parser=arg_validators.Ease.type_parser,
        metavar=arg_validators.Ease.METAVAR,
        help="Easing function to use for character movement.",
    )  # type: ignore[assignment]
    "easing.EasingFunction : Easing function to use for character movement."

    @classmethod
    def get_effect_class(cls):
        return SlideEffect


class SlideEffect:
    """Effect that slides characters into view from outside the terminal. Characters are grouped by column, row, or diagonal."""

    def __init__(
        self,
        input_data: str,
        effect_config: EffectConfig = EffectConfig(),
        terminal_config: TerminalConfig = TerminalConfig(),
    ):
        """Initializes the effect.

        Args:
            input_data (str): The input data to apply the effect to.
            effect_config (EffectConfig): The configuration for the effect.
            terminal_config (TerminalConfig): The configuration for the terminal.
        """
        self.terminal = Terminal(input_data, terminal_config)
        self.config = effect_config
        self._built = False
        self._pending_chars: list[EffectCharacter] = []
        self._active_chars: list[EffectCharacter] = []
        self._pending_groups: list[list[EffectCharacter]] = []
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def build(self) -> None:
        """Prepares the data for the effect by setting starting coordinates and building Paths/Scenes."""
        self._grouping: str = self.config.grouping
        self._reverse_direction: bool = self.config.reverse_direction
        self._merge: bool = self.config.merge
        self._gap = self.config.gap
        self._gradient_stops = self.config.final_gradient_stops
        self._easing = self.config.movement_easing
        self._pending_chars.clear()
        self._active_chars.clear()
        self._character_final_color_map.clear()
        self._pending_groups.clear()

        final_gradient = graphics.Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.config.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self._character_final_color_map[character] = final_gradient_mapping[character.input_coord]

        groups: list[list[EffectCharacter]] = []
        if self._grouping == "row":
            groups = self.terminal.get_characters_grouped(self.terminal.CharacterGroup.ROW_TOP_TO_BOTTOM)
        elif self._grouping == "column":
            groups = self.terminal.get_characters_grouped(self.terminal.CharacterGroup.COLUMN_LEFT_TO_RIGHT)
        elif self._grouping == "diagonal":
            groups = self.terminal.get_characters_grouped(
                self.terminal.CharacterGroup.DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT
            )
        for group in groups:
            for character in group:
                input_path = character.motion.new_path(
                    id="input_path", speed=self.config.movement_speed, ease=self._easing
                )
                input_path.new_waypoint(character.input_coord)

        for group_index, group in enumerate(groups):
            if self._grouping == "row":
                if self._merge and group_index % 2 == 0:
                    starting_column = self.terminal.output_area.right + 1
                else:
                    groups[group_index] = groups[group_index][::-1]
                    starting_column = self.terminal.output_area.left - 1
                if self._reverse_direction and not self._merge:
                    groups[group_index] = groups[group_index][::-1]
                    starting_column = self.terminal.output_area.right + 1
                for character in groups[group_index]:
                    character.motion.set_coordinate(geometry.Coord(starting_column, character.input_coord.row))
            elif self._grouping == "column":
                if self._merge and group_index % 2 == 0:
                    starting_row = self.terminal.output_area.bottom - 1
                else:
                    groups[group_index] = groups[group_index][::-1]
                    starting_row = self.terminal.output_area.top + 1
                if self._reverse_direction and not self._merge:
                    groups[group_index] = groups[group_index][::-1]
                    starting_row = self.terminal.output_area.bottom - 1
                for character in groups[group_index]:
                    character.motion.set_coordinate(geometry.Coord(character.input_coord.column, starting_row))
            if self._grouping == "diagonal":
                distance_from_outside_bottom = group[-1].input_coord.row - (self.terminal.output_area.bottom - 1)
                starting_coord = geometry.Coord(
                    group[-1].input_coord.column - distance_from_outside_bottom,
                    group[-1].input_coord.row - distance_from_outside_bottom,
                )
                if self._merge and group_index % 2 == 0:
                    groups[group_index] = groups[group_index][::-1]
                    distance_from_outside = (self.terminal.output_area.top + 1) - group[0].input_coord.row
                    starting_coord = geometry.Coord(
                        group[0].input_coord.column + distance_from_outside,
                        group[0].input_coord.row + distance_from_outside,
                    )
                if self._reverse_direction and not self._merge:
                    groups[group_index] = groups[group_index][::-1]
                    distance_from_outside = (self.terminal.output_area.top + 1) - group[0].input_coord.row
                    starting_coord = geometry.Coord(
                        group[0].input_coord.column + distance_from_outside,
                        group[0].input_coord.row + distance_from_outside,
                    )

                for character in groups[group_index]:
                    character.motion.set_coordinate(starting_coord)
            for character in group:
                gradient_scn = character.animation.new_scene()
                char_gradient = graphics.Gradient(
                    self._gradient_stops[0], self._character_final_color_map[character], steps=10
                )
                gradient_scn.apply_gradient_to_symbols(
                    char_gradient, character.input_symbol, self.config.final_gradient_frames
                )
                character.animation.activate_scene(gradient_scn)

        self._pending_groups = groups
        self._built = True

    @property
    def built(self) -> bool:
        """Returns True if the effect has been built."""
        return self._built

    def __iter__(self) -> Iterator[str]:
        """Runs the effect."""
        if not self._built:
            self.build()
        active_groups: list[list[EffectCharacter]] = []
        current_gap = 0
        while self._pending_groups or self._active_chars or active_groups:
            if current_gap == self._gap and self._pending_groups:
                active_groups.append(self._pending_groups.pop(0))
                current_gap = 0
            else:
                if self._pending_groups:
                    current_gap += 1
            for group in active_groups:
                if group:
                    next_char = group.pop(0)
                    self.terminal.set_character_visibility(next_char, True)
                    next_char.motion.activate_path(next_char.motion.paths["input_path"])
                    self._active_chars.append(next_char)
            active_groups = [group for group in active_groups if group]
            yield self.terminal.get_formatted_output_string()
            self._animate_chars()

            self._active_chars = [character for character in self._active_chars if character.is_active]
        self._built = False

    def _animate_chars(self) -> None:
        """Animates the characters by calling the tick method on all active characters."""
        for character in self._active_chars:
            character.tick()
