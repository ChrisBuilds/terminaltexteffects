import argparse
import random
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils.terminal import Terminal
from terminaltexteffects.utils import graphics, motion, argtypes


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "synthgrid",
        formatter_class=argtypes.CustomFormatter,
        help="Create a grid which fills with characters dissolving into the final text.",
        description="Create a grid which fills with characters dissolving into the final text.",
        epilog=f"""Example: terminaltexteffects synthgrid --grid-gradient-stops CC00CC ffffff --text-gradient-stops 8A008A 00D1FF FFFFFF --grid-row-symbol - --grid-column-symbol | --max-active-blocks 0.1 --text-generation-symbols ░ ▒ ▓""",
    )
    effect_parser.set_defaults(effect_class=SynthGridEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.nonnegative_float,
        default=0.01,
        help="Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have no impact beyond a certain lower threshold due to the processing speed of your device.",
    )
    effect_parser.add_argument(
        "--grid-gradient-stops",
        type=argtypes.color,
        nargs="*",
        default=["CC00CC", "ffffff"],
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the grid gradient.",
    )
    effect_parser.add_argument(
        "--text-gradient-stops",
        type=argtypes.color,
        nargs="*",
        default=["8A008A", "00D1FF", "FFFFFF"],
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the text gradient.",
    )
    effect_parser.add_argument(
        "--grid-row-symbol",
        type=argtypes.symbol,
        default="─",
        metavar="(single character)",
        help="Symbol to use for grid row lines.",
    )
    effect_parser.add_argument(
        "--grid-column-symbol",
        type=argtypes.symbol,
        default="│",
        metavar="(single character)",
        help="Symbol to use for grid column lines.",
    )
    effect_parser.add_argument(
        "--text-generation-symbols",
        type=argtypes.symbol,
        nargs="*",
        default=["░", "▒", "▓"],
        metavar="(characters)",
        help="Space separated, unquoted, list of characters for the text generation animation.",
    )
    effect_parser.add_argument(
        "--max-active-blocks",
        type=argtypes.positive_float,
        default=0.1,
        metavar="(0 < n <= 1.0)",
        help="Maximum percentage of blocks to have active at any given time. For example, if set to 0.1, 10% of the blocks will be active at any given time.",
    )


class GridLine:
    def __init__(self, terminal: Terminal, args: argparse.Namespace, origin: motion.Coord, direction: str):
        self.terminal = terminal
        self.args = args
        self.origin = origin
        self.direction = direction
        if self.direction == "horizontal":
            self.grid_symbol = self.args.grid_row_symbol
            self.gradient = graphics.Gradient(self.args.grid_gradient_stops, self.terminal.output_area.top)
        elif self.direction == "vertical":
            self.grid_symbol = self.args.grid_column_symbol
            self.gradient = graphics.Gradient(
                self.args.grid_gradient_stops, max(self.terminal.output_area.top - self.terminal.output_area.bottom, 1)
            )
        self.characters: list[EffectCharacter] = []
        if direction == "horizontal":
            for column_index in range(self.terminal.output_area.left, self.terminal.output_area.right):
                effect_char = self.terminal.add_character(self.grid_symbol)
                grid_scn = effect_char.animation.new_scene()
                grid_scn.add_frame(self.grid_symbol, 1, color=self.gradient.spectrum[self.origin.row - 1])
                effect_char.animation.activate_scene(grid_scn)
                effect_char.layer = 2
                effect_char.motion.set_coordinate(motion.Coord(column_index, origin.row))
                self.characters.append(effect_char)
        elif direction == "vertical":
            for row_index in range(self.terminal.output_area.bottom, self.terminal.output_area.top):
                effect_char = self.terminal.add_character(self.grid_symbol)
                grid_scn = effect_char.animation.new_scene()
                grid_scn.add_frame(self.grid_symbol, 1, color=self.gradient.spectrum.pop(0))
                effect_char.animation.activate_scene(grid_scn)
                effect_char.layer = 2
                effect_char.motion.set_coordinate(motion.Coord(origin.column, row_index))
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
                next_char.is_visible = True
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
                next_char.is_visible = False
                self.collapsed_characters.append(next_char)

    def is_extended(self) -> bool:
        return not self.collapsed_characters

    def is_collapsed(self) -> bool:
        return not self.extended_characters


class SynthGridEffect:
    """Effect that creates a grid where blocks of characters dissolved into the input characters."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_groups: list[tuple[int, list[EffectCharacter]]] = []
        self.animating_chars: list[EffectCharacter] = []
        self.grid_lines: list[GridLine] = []
        self.group_tracker: dict[int, int] = {}

    def find_even_gap(self, length: int) -> int:
        length = length - 2
        if length <= 0:
            return 0
        for i in range(20, 4, -1):
            if length % i <= 1:
                return i
        return 4

    def prepare_data(self) -> None:
        """Prepares the data for the effect by ___."""
        self.grid_lines.append(
            GridLine(
                self.terminal,
                self.args,
                motion.Coord(self.terminal.output_area.left, self.terminal.output_area.bottom),
                "horizontal",
            )
        )
        self.grid_lines.append(
            GridLine(
                self.terminal,
                self.args,
                motion.Coord(self.terminal.output_area.left, self.terminal.output_area.top),
                "horizontal",
            )
        )
        self.grid_lines.append(
            GridLine(
                self.terminal,
                self.args,
                motion.Coord(self.terminal.output_area.left, self.terminal.output_area.bottom),
                "vertical",
            )
        )
        self.grid_lines.append(
            GridLine(
                self.terminal,
                self.args,
                motion.Coord(self.terminal.output_area.right, self.terminal.output_area.bottom),
                "vertical",
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
            row_indexes.append(row_index)
            self.grid_lines.append(
                GridLine(
                    self.terminal, self.args, motion.Coord(self.terminal.output_area.left, row_index), "horizontal"
                )
            )
        for column_index in range(
            self.terminal.output_area.left + column_gap, self.terminal.output_area.right, max(column_gap, 1)
        ):
            column_indexes.append(column_index)
            self.grid_lines.append(
                GridLine(
                    self.terminal, self.args, motion.Coord(column_index, self.terminal.output_area.bottom), "vertical"
                )
            )
        output_gradient = graphics.Gradient(self.args.text_gradient_stops, 10)
        if not row_indexes:
            row_indexes.append(self.terminal.output_area.top)
        else:
            row_indexes.append(row_indexes[-1] + row_gap)
        if not column_indexes:
            column_indexes.append(self.terminal.output_area.right)
        else:
            column_indexes.append(column_indexes[-1] + column_gap)
        prev_row_index = 1
        for row_index in row_indexes:
            prev_column_index = 1
            for column_index in column_indexes:
                coords_in_block: list[tuple[int, int]] = []
                if row_index == self.terminal.output_area.top:  # make sure the top row is included
                    row_index += 1
                for row in range(prev_row_index, row_index):
                    for column in range(prev_column_index, column_index):
                        coords_in_block.append((column, row))
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
                text_gradient_index = round(
                    (character.input_coord.row / self.terminal.output_area.top) * (len(output_gradient.spectrum) - 1)
                )

                dissolve_scn = character.animation.new_scene()
                for _ in range(random.randint(15, 30)):
                    dissolve_scn.add_frame(
                        random.choice(self.args.text_generation_symbols),
                        3,
                        color=random.choice(output_gradient.spectrum),
                    )
                dissolve_scn.add_frame(character.input_symbol, 1, color=output_gradient.spectrum[text_gradient_index])
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
            for character in self.terminal.characters:
                character.is_visible = True
                self.animating_chars.append(character)
        active_groups: int = 0
        while self.pending_groups or self.animating_chars or phase != "complete":
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
                        char.is_visible = True
                        self.animating_chars.append(char)
                        self.group_tracker[group_number] += 1
                if not self.pending_groups and not self.animating_chars and not active_groups:
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

            # remove completed chars from animating chars
            self.animating_chars = [
                animating_char for animating_char in self.animating_chars if animating_char.is_active()
            ]
            # active_groups = [group for group in active_groups if any([char in self.animating_chars for char in group])]
            active_groups = 0
            for _, active_count in self.group_tracker.items():
                if active_count:
                    active_groups += 1

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method on all active characters."""
        for animating_char in self.animating_chars:
            animating_char.tick()
