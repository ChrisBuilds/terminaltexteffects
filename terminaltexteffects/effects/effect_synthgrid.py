"""Create a grid which fills with characters dissolving into the final text.

Classes:
    SynthGrid: Create a grid which fills with characters dissolving into the final text.
    SynthGridConfig: Configuration for the SynthGrid effect.
    SynthGridIterator: Iterates over the effect. Does not normally need to be called directly.
"""

import random
import typing
from dataclasses import dataclass

from terminaltexteffects.engine.base_character import EffectCharacter, EventHandler
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.terminal import Terminal
from terminaltexteffects.utils import argvalidators, geometry
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.graphics import Color, Gradient


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return SynthGrid, SynthGridConfig


@argclass(
    name="synthgrid",
    help="Create a grid which fills with characters dissolving into the final text.",
    description="synthgrid | Create a grid which fills with characters dissolving into the final text.",
    epilog="""Example: terminaltexteffects synthgrid --grid-gradient-stops CC00CC ffffff --grid-gradient-steps 12 --text-gradient-stops 8A008A 00D1FF FFFFFF --text-gradient-steps 12 --grid-row-symbol ─ --grid-column-symbol "│" --text-generation-symbols ░ ▒ ▓ --max-active-blocks 0.1""",
)
@dataclass
class SynthGridConfig(ArgsDataClass):
    """Configuration for the SynthGrid effect.

    Attributes:
        grid_gradient_stops (tuple[Color, ...]): Tuple of colors for the grid gradient.
        grid_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. Valid values are n > 0.
        grid_gradient_direction (Gradient.Direction): Direction of the gradient for the grid color.
        text_gradient_stops (tuple[Color, ...]): Tuple of colors for the text gradient.
        text_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. Valid values are n > 0.
        text_gradient_direction (Gradient.Direction): Direction of the gradient for the text color.
        grid_row_symbol (str): Symbol to use for grid row lines.
        grid_column_symbol (str): Symbol to use for grid column lines.
        text_generation_symbols (tuple[str, ...] | str): Tuple of characters for the text generation animation.
        max_active_blocks (float): Maximum percentage of blocks to have active at any given time. For example, if set to 0.1, 10 percent of the blocks will be active at any given time. Valid values are 0 < n <= 1."""

    grid_gradient_stops: tuple[Color, ...] = ArgField(
        cmd_name=["--grid-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("CC00CC"), Color("ffffff")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the grid gradient.",
    )  # type: ignore[assignment]
    "tuple[Color, ...] : Tuple of colors for the grid gradient."

    grid_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--grid-gradient-steps",
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    grid_gradient_direction: Gradient.Direction = ArgField(
        cmd_name="--grid-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=Gradient.Direction.DIAGONAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the gradient for the grid color.",
    )  # type: ignore[assignment]
    "Gradient.Direction : Direction of the gradient for the grid color."

    text_gradient_stops: tuple[Color, ...] = ArgField(
        cmd_name=["--text-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("8A008A"), Color("00D1FF"), Color("FFFFFF")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the text gradient.",
    )  # type: ignore[assignment]
    "tuple[Color, ...] : Tuple of colors for the text gradient."

    text_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--text-gradient-steps",
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    text_gradient_direction: Gradient.Direction = ArgField(
        cmd_name="--text-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=Gradient.Direction.VERTICAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the gradient for the text color.",
    )  # type: ignore[assignment]
    "Gradient.Direction : Direction of the gradient for the text color."

    grid_row_symbol: str = ArgField(
        cmd_name="--grid-row-symbol",
        type_parser=argvalidators.Symbol.type_parser,
        default="─",
        metavar=argvalidators.Symbol.METAVAR,
        help="Symbol to use for grid row lines.",
    )  # type: ignore[assignment]
    "str : Symbol to use for grid row lines."

    grid_column_symbol: str = ArgField(
        cmd_name="--grid-column-symbol",
        type_parser=argvalidators.Symbol.type_parser,
        default="│",
        metavar=argvalidators.Symbol.METAVAR,
        help="Symbol to use for grid column lines.",
    )  # type: ignore[assignment]
    "str : Symbol to use for grid column lines."

    text_generation_symbols: tuple[str, ...] = ArgField(
        cmd_name="--text-generation-symbols",
        type_parser=argvalidators.Symbol.type_parser,
        nargs="+",
        default=("░", "▒", "▓"),
        metavar=argvalidators.Symbol.METAVAR,
        help="Space separated, unquoted, list of characters for the text generation animation.",
    )  # type: ignore[assignment]
    "tuple[str, ...] : Tuple of characters for the text generation animation."

    max_active_blocks: float = ArgField(
        cmd_name="--max-active-blocks",
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=0.1,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Maximum percentage of blocks to have active at any given time. For example, if set to 0.1, 10 percent of the blocks will be active at any given time.",
    )  # type: ignore[assignment]
    "float : Maximum percentage of blocks to have active at any given time."

    @classmethod
    def get_effect_class(cls):
        return SynthGrid


class GridLine:
    def __init__(
        self,
        terminal: Terminal,
        args: SynthGridConfig,
        origin: Coord,
        direction: str,
        grid_gradient_mapping: dict[geometry.Coord, Color],
    ):
        self.terminal = terminal
        self.args = args
        self.origin = origin
        self.direction = direction
        if self.direction == "horizontal":
            self.grid_symbol = self.args.grid_row_symbol
        elif self.direction == "vertical":
            self.grid_symbol = self.args.grid_column_symbol
        self.characters: list[EffectCharacter] = []
        if direction == "horizontal":
            for column_index in range(self.terminal.canvas.left, self.terminal.canvas.right + 1):
                effect_char = self.terminal.add_character(self.grid_symbol, Coord(0, 0))
                grid_scn = effect_char.animation.new_scene()
                grid_scn.add_frame(
                    self.grid_symbol, 1, color=grid_gradient_mapping[geometry.Coord(column_index, origin.row)]
                )
                effect_char.animation.activate_scene(grid_scn)
                effect_char.layer = 2
                effect_char.motion.set_coordinate(Coord(column_index, origin.row))
                self.characters.append(effect_char)
        elif direction == "vertical":
            for row_index in range(self.terminal.canvas.bottom, self.terminal.canvas.top):
                effect_char = self.terminal.add_character(self.grid_symbol, Coord(0, 0))
                grid_scn = effect_char.animation.new_scene()
                grid_scn.add_frame(
                    self.grid_symbol, 1, color=grid_gradient_mapping[geometry.Coord(origin.column, row_index)]
                )
                effect_char.animation.activate_scene(grid_scn)
                effect_char.layer = 2
                effect_char.motion.set_coordinate(Coord(origin.column, row_index))
                self.characters.append(effect_char)
        self.collapsed_characters = [effect_char for effect_char in self.characters]
        self.extended_characters: list[EffectCharacter] = []

    def extend(self) -> None:
        if self.direction == "horizontal":
            count = 3
        else:
            count = 1
        for _ in range(count):
            if self.collapsed_characters:
                next_char = self.collapsed_characters.pop(0)
                self.terminal.set_character_visibility(next_char, True)
                self.extended_characters.append(next_char)

    def collapse(self) -> None:
        if self.direction == "horizontal":
            count = 3
        else:
            count = 1
        if not self.collapsed_characters:
            self.extended_characters = self.extended_characters[::-1]
        for _ in range(count):
            if self.extended_characters:
                next_char = self.extended_characters.pop(0)
                self.terminal.set_character_visibility(next_char, False)
                self.collapsed_characters.append(next_char)

    def is_extended(self) -> bool:
        return not self.collapsed_characters

    def is_collapsed(self) -> bool:
        return not self.extended_characters


class SynthGridIterator(BaseEffectIterator[SynthGridConfig]):
    def __init__(self, effect: "SynthGrid") -> None:
        super().__init__(effect)
        self.pending_groups: list[tuple[int, list[EffectCharacter]]] = []
        self.grid_lines: list[GridLine] = []
        self.group_tracker: dict[int, int] = {}
        self.build()

    def find_even_gap(self, dimension: int) -> int:
        """Find the closest even gap to 20% of the longest dimension.

        Args:
            dimension (int): The longest dimension.

        Returns:
            int: The gap that is closest to 20% of the dimension length.
        """
        potential_gaps: list[int] = []
        dimension = dimension - 2
        if dimension <= 0:
            return 0
        for i in range(dimension, 4, -1):
            if dimension % i <= 1:
                potential_gaps.append(i)
        if not potential_gaps:
            return 4
        return min(potential_gaps, key=lambda x: abs(x - dimension // 5))

    def build(self) -> None:
        grid_gradient = Gradient(*self.config.grid_gradient_stops, steps=self.config.grid_gradient_steps)
        grid_gradient_mapping = grid_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.top, self.terminal.canvas.right, self.config.grid_gradient_direction
        )
        text_gradient = Gradient(*self.config.text_gradient_stops, steps=self.config.text_gradient_steps)
        text_gradient_mapping = text_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.top, self.terminal.canvas.right, self.config.text_gradient_direction
        )

        self.grid_lines.append(
            GridLine(
                self.terminal,
                self.config,
                Coord(self.terminal.canvas.left, self.terminal.canvas.bottom),
                "horizontal",
                grid_gradient_mapping,
            )
        )
        self.grid_lines.append(
            GridLine(
                self.terminal,
                self.config,
                Coord(self.terminal.canvas.left, self.terminal.canvas.top),
                "horizontal",
                grid_gradient_mapping,
            )
        )
        self.grid_lines.append(
            GridLine(
                self.terminal,
                self.config,
                Coord(self.terminal.canvas.left, self.terminal.canvas.bottom),
                "vertical",
                grid_gradient_mapping,
            )
        )
        self.grid_lines.append(
            GridLine(
                self.terminal,
                self.config,
                Coord(self.terminal.canvas.right, self.terminal.canvas.bottom),
                "vertical",
                grid_gradient_mapping,
            )
        )
        column_indexes: list[int] = []
        row_indexes: list[int] = []
        if self.terminal.canvas.top > 2 * self.terminal.canvas.right:
            row_gap = self.find_even_gap(self.terminal.canvas.top) + 1
            column_gap = row_gap * 2
        else:
            column_gap = self.find_even_gap(self.terminal.canvas.right) + 1
            row_gap = column_gap // 2

        for row_index in range(self.terminal.canvas.bottom + row_gap, self.terminal.canvas.top, max(row_gap, 1)):
            if self.terminal.canvas.top - row_index < 2:
                continue
            row_indexes.append(row_index)
            self.grid_lines.append(
                GridLine(
                    self.terminal,
                    self.config,
                    Coord(self.terminal.canvas.left, row_index),
                    "horizontal",
                    grid_gradient_mapping,
                )
            )
        for column_index in range(
            self.terminal.canvas.left + column_gap, self.terminal.canvas.right, max(column_gap, 1)
        ):
            if self.terminal.canvas.right - column_index < 2:
                continue
            column_indexes.append(column_index)
            self.grid_lines.append(
                GridLine(
                    self.terminal,
                    self.config,
                    Coord(column_index, self.terminal.canvas.bottom),
                    "vertical",
                    grid_gradient_mapping,
                )
            )
        row_indexes.append(self.terminal.canvas.top + 1)
        column_indexes.append(self.terminal.canvas.right + 1)
        prev_row_index = 1
        for row_index in row_indexes:
            prev_column_index = 1
            for column_index in column_indexes:
                coords_in_block: list[Coord] = []
                if row_index == self.terminal.canvas.top:  # make sure the top row is included
                    row_index += 1
                for row in range(prev_row_index, row_index):
                    for column in range(prev_column_index, column_index):
                        coords_in_block.append(Coord(column, row))
                characters_in_block: list[EffectCharacter] = []
                for coord in coords_in_block:
                    if coord in self.terminal.character_by_input_coord:
                        characters_in_block.append(self.terminal.character_by_input_coord[coord])
                if characters_in_block:
                    self.pending_groups.append((len(self.pending_groups), characters_in_block))
                prev_column_index = column_index
            prev_row_index = row_index
        for group_number, group in self.pending_groups:
            self.group_tracker[group_number] = 0
            for character in group:
                dissolve_scn = character.animation.new_scene()
                for _ in range(random.randint(15, 30)):
                    dissolve_scn.add_frame(
                        random.choice(self.config.text_generation_symbols),
                        3,
                        color=random.choice(text_gradient.spectrum),
                    )
                dissolve_scn.add_frame(character.input_symbol, 1, color=text_gradient_mapping[character.input_coord])
                character.animation.activate_scene(dissolve_scn)
                character.event_handler.register_event(
                    EventHandler.Event.SCENE_COMPLETE,
                    dissolve_scn,
                    EventHandler.Action.CALLBACK,
                    EventHandler.Callback(self.update_group_tracker, group_number),
                )
        random.shuffle(self.pending_groups)
        self._phase = "grid_expand"
        self._total_group_count = len(self.pending_groups)
        if not self._total_group_count:
            for character in self.terminal.get_characters():
                self.terminal.set_character_visibility(character, True)
                self.active_characters.append(character)
        self._active_groups: int = 0

    def update_group_tracker(self, character: EffectCharacter, *args) -> None:
        self.group_tracker[args[0]] -= 1

    def __next__(self) -> str:
        if self.pending_groups or self.active_characters or self._phase != "complete":
            if self._phase == "grid_expand":
                if not all([grid_line.is_extended() for grid_line in self.grid_lines]):
                    for grid_line in self.grid_lines:
                        if not grid_line.is_extended():
                            grid_line.extend()
                else:
                    self._phase = "add_chars"
            elif self._phase == "add_chars":
                if (
                    self.pending_groups
                    and self._active_groups < self._total_group_count * self.config.max_active_blocks
                ):
                    group_number, next_group = self.pending_groups.pop(0)
                    for char in next_group:
                        self.terminal.set_character_visibility(char, True)
                        self.active_characters.append(char)
                        self.group_tracker[group_number] += 1
                if not self.pending_groups and not self.active_characters and not self._active_groups:
                    self._phase = "collapse"
            elif self._phase == "collapse":
                if not all([grid_line.is_collapsed() for grid_line in self.grid_lines]):
                    for grid_line in self.grid_lines:
                        if not grid_line.is_collapsed():
                            grid_line.collapse()
                else:
                    self._phase = "complete"
            self.update()
            self._active_groups = 0
            for _, active_count in self.group_tracker.items():
                if active_count:
                    self._active_groups += 1
            return self.frame
        else:
            raise StopIteration


class SynthGrid(BaseEffect[SynthGridConfig]):
    """Create a grid which fills with characters dissolving into the final text.

    Attributes:
        effect_config (SynthGridConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.
    """

    _config_cls = SynthGridConfig
    _iterator_cls = SynthGridIterator

    def __init__(self, input_data: str) -> None:
        """Initialize the effect with the provided input data.

        Args:
            input_data (str): The input data to use for the effect."""
        super().__init__(input_data)
