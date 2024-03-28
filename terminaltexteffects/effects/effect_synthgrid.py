import random
import typing
from dataclasses import dataclass

from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils import arg_validators, geometry, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return SynthGridEffect, SynthGridEffectArgs


@argclass(
    name="synthgrid",
    formatter_class=arg_validators.CustomFormatter,
    help="Create a grid which fills with characters dissolving into the final text.",
    description="synthgrid | Create a grid which fills with characters dissolving into the final text.",
    epilog="""Example: terminaltexteffects synthgrid --grid-gradient-stops CC00CC ffffff --grid-gradient-steps 12 --text-gradient-stops 8A008A 00D1FF FFFFFF --text-gradient-steps 12 --grid-row-symbol ─ --grid-column-symbol "│" --text-generation-symbols ░ ▒ ▓ --max-active-blocks 0.1""",
)
@dataclass
class SynthGridEffectArgs(ArgsDataClass):
    grid_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--grid-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("CC00CC", "ffffff"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the grid gradient.",
    )  # type: ignore[assignment]
    grid_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--grid-gradient-steps",
        type_parser=arg_validators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    grid_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--grid-gradient-direction",
        type_parser=arg_validators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.DIAGONAL,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the gradient for the grid color.",
    )  # type: ignore[assignment]
    text_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--text-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("8A008A", "00D1FF", "FFFFFF"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the text gradient.",
    )  # type: ignore[assignment]
    text_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--text-gradient-steps",
        type_parser=arg_validators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    text_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--text-gradient-direction",
        type_parser=arg_validators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.VERTICAL,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the gradient for the text color.",
    )  # type: ignore[assignment]
    grid_row_symbol: str = ArgField(
        cmd_name="--grid-row-symbol",
        type_parser=arg_validators.Symbol.type_parser,
        default="─",
        metavar=arg_validators.Symbol.METAVAR,
        help="Symbol to use for grid row lines.",
    )  # type: ignore[assignment]
    grid_column_symbol: str = ArgField(
        cmd_name="--grid-column-symbol",
        type_parser=arg_validators.Symbol.type_parser,
        default="│",
        metavar=arg_validators.Symbol.METAVAR,
        help="Symbol to use for grid column lines.",
    )  # type: ignore[assignment]
    text_generation_symbols: tuple[str, ...] = ArgField(
        cmd_name="--text-generation-symbols",
        type_parser=arg_validators.Symbol.type_parser,
        nargs="+",
        default=("░", "▒", "▓"),
        metavar=arg_validators.Symbol.METAVAR,
        help="Space separated, unquoted, list of characters for the text generation animation.",
    )  # type: ignore[assignment]
    max_active_blocks: float = ArgField(
        cmd_name="--max-active-blocks",
        type_parser=arg_validators.PositiveFloat.type_parser,
        default=0.1,
        metavar=arg_validators.PositiveFloat.METAVAR,
        help="Maximum percentage of blocks to have active at any given time. For example, if set to 0.1, 10 percent of the blocks will be active at any given time.",
    )  # type: ignore[assignment]

    @classmethod
    def get_effect_class(cls):
        return SynthGridEffect


class GridLine:
    def __init__(
        self,
        terminal: Terminal,
        args: SynthGridEffectArgs,
        origin: Coord,
        direction: str,
        grid_gradient_mapping: dict[geometry.Coord, graphics.Color],
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
            for column_index in range(self.terminal.output_area.left, self.terminal.output_area.right + 1):
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
            for row_index in range(self.terminal.output_area.bottom, self.terminal.output_area.top):
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


class SynthGridEffect:
    """Effect that creates a grid where blocks of characters dissolved into the input characters."""

    def __init__(self, terminal: Terminal, args: SynthGridEffectArgs):
        self.terminal = terminal
        self.args = args
        self.pending_groups: list[tuple[int, list[EffectCharacter]]] = []
        self.active_chars: list[EffectCharacter] = []
        self.grid_lines: list[GridLine] = []
        self.group_tracker: dict[int, int] = {}

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

    def prepare_data(self) -> None:
        grid_gradient = graphics.Gradient(*self.args.grid_gradient_stops, steps=self.args.grid_gradient_steps)
        grid_gradient_mapping = grid_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.args.grid_gradient_direction
        )
        text_gradient = graphics.Gradient(*self.args.text_gradient_stops, steps=self.args.text_gradient_steps)
        text_gradient_mapping = text_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.args.text_gradient_direction
        )

        self.grid_lines.append(
            GridLine(
                self.terminal,
                self.args,
                Coord(self.terminal.output_area.left, self.terminal.output_area.bottom),
                "horizontal",
                grid_gradient_mapping,
            )
        )
        self.grid_lines.append(
            GridLine(
                self.terminal,
                self.args,
                Coord(self.terminal.output_area.left, self.terminal.output_area.top),
                "horizontal",
                grid_gradient_mapping,
            )
        )
        self.grid_lines.append(
            GridLine(
                self.terminal,
                self.args,
                Coord(self.terminal.output_area.left, self.terminal.output_area.bottom),
                "vertical",
                grid_gradient_mapping,
            )
        )
        self.grid_lines.append(
            GridLine(
                self.terminal,
                self.args,
                Coord(self.terminal.output_area.right, self.terminal.output_area.bottom),
                "vertical",
                grid_gradient_mapping,
            )
        )
        column_indexes: list[int] = []
        row_indexes: list[int] = []
        if self.terminal.output_area.top > 2 * self.terminal.output_area.right:
            row_gap = self.find_even_gap(self.terminal.output_area.top) + 1
            column_gap = row_gap * 2
        else:
            column_gap = self.find_even_gap(self.terminal.output_area.right) + 1
            row_gap = column_gap // 2

        for row_index in range(
            self.terminal.output_area.bottom + row_gap, self.terminal.output_area.top, max(row_gap, 1)
        ):
            if self.terminal.output_area.top - row_index < 2:
                continue
            row_indexes.append(row_index)
            self.grid_lines.append(
                GridLine(
                    self.terminal,
                    self.args,
                    Coord(self.terminal.output_area.left, row_index),
                    "horizontal",
                    grid_gradient_mapping,
                )
            )
        for column_index in range(
            self.terminal.output_area.left + column_gap, self.terminal.output_area.right, max(column_gap, 1)
        ):
            if self.terminal.output_area.right - column_index < 2:
                continue
            column_indexes.append(column_index)
            self.grid_lines.append(
                GridLine(
                    self.terminal,
                    self.args,
                    Coord(column_index, self.terminal.output_area.bottom),
                    "vertical",
                    grid_gradient_mapping,
                )
            )
        row_indexes.append(self.terminal.output_area.top + 1)
        column_indexes.append(self.terminal.output_area.right + 1)
        prev_row_index = 1
        for row_index in row_indexes:
            prev_column_index = 1
            for column_index in column_indexes:
                coords_in_block: list[Coord] = []
                if row_index == self.terminal.output_area.top:  # make sure the top row is included
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
                        random.choice(self.args.text_generation_symbols),
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

    def update_group_tracker(self, character: EffectCharacter, *args) -> None:
        self.group_tracker[args[0]] -= 1

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        phase = "grid_expand"
        total_group_count = len(self.pending_groups)
        if not total_group_count:
            for character in self.terminal.get_characters():
                self.terminal.set_character_visibility(character, True)
                self.active_chars.append(character)
        active_groups: int = 0
        while self.pending_groups or self.active_chars or phase != "complete":
            if phase == "grid_expand":
                if not all([grid_line.is_extended() for grid_line in self.grid_lines]):
                    for grid_line in self.grid_lines:
                        if not grid_line.is_extended():
                            grid_line.extend()
                else:
                    phase = "add_chars"
            elif phase == "add_chars":
                if self.pending_groups and active_groups < total_group_count * self.args.max_active_blocks:
                    group_number, next_group = self.pending_groups.pop(0)
                    for char in next_group:
                        self.terminal.set_character_visibility(char, True)
                        self.active_chars.append(char)
                        self.group_tracker[group_number] += 1
                if not self.pending_groups and not self.active_chars and not active_groups:
                    phase = "collapse"
            elif phase == "collapse":
                if not all([grid_line.is_collapsed() for grid_line in self.grid_lines]):
                    for grid_line in self.grid_lines:
                        if not grid_line.is_collapsed():
                            grid_line.collapse()
                else:
                    phase = "complete"
            self.terminal.print()
            self.animate_chars()

            self.active_chars = [character for character in self.active_chars if character.is_active]
            active_groups = 0
            for _, active_count in self.group_tracker.items():
                if active_count:
                    active_groups += 1

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method on all active characters."""
        for character in self.active_chars:
            character.tick()
