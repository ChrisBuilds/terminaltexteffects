import random
import typing
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils import graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return OverflowEffect, OverflowEffectArgs


@argclass(
    name="overflow",
    formatter_class=arg_validators.CustomFormatter,
    help="Input text overflows ands scrolls the terminal in a random order until eventually appearing ordered.",
    description="overflow | Input text overflows ands scrolls the terminal in a random order until eventually appearing ordered.",
    epilog="""Example: terminaltexteffects overflow --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --overflow-gradient-stops f2ebc0 8dbfb3 f2ebc0 --overflow-cycles-range 2-4 --overflow-speed 3""",
)
@dataclass
class OverflowEffectArgs(ArgsDataClass):
    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("8A008A", "00D1FF", "FFFFFF"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name=["--final-gradient-steps"],
        type_parser=arg_validators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=arg_validators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.VERTICAL,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the gradient for the final color.",
    )  # type: ignore[assignment]
    overflow_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--overflow-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("f2ebc0", "8dbfb3", "f2ebc0"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the overflow gradient.",
    )  # type: ignore[assignment]
    overflow_cycles_range: tuple[int, int] = ArgField(
        cmd_name=["--overflow-cycles-range"],
        type_parser=arg_validators.IntRange.type_parser,
        default=(2, 4),
        metavar=arg_validators.IntRange.METAVAR,
        help="Number of cycles to overflow the text.",
    )  # type: ignore[assignment]
    overflow_speed: int = ArgField(
        cmd_name=["--overflow-speed"],
        type_parser=arg_validators.PositiveInt.type_parser,
        default=3,
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Speed of the overflow effect.",
    )  # type: ignore[assignment]

    @classmethod
    def get_effect_class(cls):
        return OverflowEffect


class Row:
    def __init__(self, characters: list[EffectCharacter], final: bool = False) -> None:
        self.characters = characters
        self.current_index = 0
        self.final = final

    def move_up(self) -> None:
        for character in self.characters:
            current_row = character.motion.current_coord.row
            character.motion.set_coordinate(Coord(character.motion.current_coord.column, current_row + 1))

    def setup(self) -> None:
        for character in self.characters:
            character.motion.set_coordinate(Coord(character.input_coord.column, 0))

    def set_color(self, color: int | str) -> None:
        for character in self.characters:
            character.animation.set_appearance(character.input_symbol, color)


class OverflowEffect:
    def __init__(self, terminal: Terminal, args: OverflowEffectArgs):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.pending_rows: list[Row] = []
        self.active_rows: list[Row] = []
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_data(self) -> None:
        final_gradient = graphics.Gradient(*self.args.final_gradient_stops, steps=self.args.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.args.final_gradient_direction
        )
        for character in self.terminal.get_characters(fill_chars=True):
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
        lower_range, upper_range = self.args.overflow_cycles_range
        rows = self.terminal.get_characters_grouped(Terminal.CharacterGroup.ROW_TOP_TO_BOTTOM)
        if upper_range > 0:
            for _ in range(random.randint(lower_range, upper_range)):
                random.shuffle(rows)
                for row in rows:
                    copied_characters = [
                        self.terminal.add_character(character.input_symbol, character.input_coord) for character in row
                    ]
                    self.pending_rows.append(Row(copied_characters))
        # add rows in correct order to the end of self.pending_rows
        for row in self.terminal.get_characters_grouped(Terminal.CharacterGroup.ROW_TOP_TO_BOTTOM, fill_chars=True):
            next_row = Row(row)
            for character in next_row.characters:
                character.animation.set_appearance(character.symbol, self.character_final_color_map[character])
            next_row.set_color(
                final_gradient.get_color_at_fraction(row[0].input_coord.row / self.terminal.output_area.top)
            )
            self.pending_rows.append(Row(row, final=True))

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        delay = 0
        g = graphics.Gradient(
            *self.args.overflow_gradient_stops,
            steps=max((self.terminal.output_area.top // max(1, len(self.args.overflow_gradient_stops) - 1)), 1),
        )

        while self.pending_rows:
            if not delay:
                for _ in range(random.randint(1, self.args.overflow_speed)):
                    if self.pending_rows:
                        for row in self.active_rows:
                            row.move_up()
                            if not row.final:
                                row.set_color(
                                    g.spectrum[min(row.characters[0].motion.current_coord.row, len(g.spectrum) - 1)]
                                )
                        next_row = self.pending_rows.pop(0)
                        next_row.setup()
                        next_row.move_up()
                        if not next_row.final:
                            next_row.set_color(g.spectrum[0])
                        for character in next_row.characters:
                            self.terminal.set_character_visibility(character, True)
                        self.active_rows.append(next_row)
                delay = random.randint(0, 3)

            else:
                delay -= 1
            self.active_rows = [
                row
                for row in self.active_rows
                if row.characters[0].motion.current_coord.row <= self.terminal.output_area.top
            ]
            self.terminal.print()
            self.animate_chars()

            self.active_chars = [character for character in self.active_chars if character.is_active]

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method on all active characters."""
        for character in self.active_chars:
            character.tick()
