import typing
from dataclasses import dataclass

from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils import argtypes, easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return VerticalSlice, VerticalSliceArgs


@argclass(
    name="verticalslice",
    formatter_class=argtypes.CustomFormatter,
    help="Slices the input in half vertically and slides it into place from opposite directions.",
    description="verticalslice | Slices the input in half vertically and slides it into place from opposite directions.",
    epilog=f"""{argtypes.EASING_EPILOG}
    
Example: terminaltexteffects verticalslice --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --movement-speed 0.5 --movement-easing IN_OUT_EXPO""",
)
@dataclass
class VerticalSliceArgs(ArgsDataClass):
    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argtypes.Color.type_parser,
        nargs="+",
        default=("8A008A", "00D1FF", "FFFFFF"),
        metavar=argtypes.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=argtypes.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=argtypes.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    movement_speed: float = ArgField(
        cmd_name="--movement-speed",
        type_parser=argtypes.PositiveFloat.type_parser,
        default=0.5,
        metavar=argtypes.PositiveFloat.METAVAR,
        help="Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )  # type: ignore[assignment]
    movement_easing: easing.EasingFunction = ArgField(
        cmd_name="--movement-easing",
        type_parser=argtypes.Ease.type_parser,
        default=easing.in_out_expo,
        help="Easing function to use for character movement.",
    )  # type: ignore[assignment]

    @classmethod
    def get_effect_class(cls):
        return VerticalSlice


class VerticalSlice:
    """Effect that slices the input in half vertically and slides it into place from opposite directions."""

    def __init__(self, terminal: Terminal, args: VerticalSliceArgs):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.new_rows: list[list[EffectCharacter]] = []
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_data(self) -> None:
        """Prepares the data for the effect by setting the left half to start at the top and the
        right half to start at the bottom, and creating rows consisting off halves from opposite
        input rows."""
        final_gradient = graphics.Gradient(*self.args.final_gradient_stops, steps=self.args.final_gradient_steps)

        for character in self.terminal.get_characters():
            character.animation.set_appearance(
                character.input_symbol,
                final_gradient.get_color_at_fraction(character.input_coord.row / self.terminal.output_area.top),
            )

        self.rows = self.terminal.get_characters_grouped(grouping=self.terminal.CharacterGroup.ROW_BOTTOM_TO_TOP)
        lengths = [max([c.input_coord.column for c in row]) for row in self.rows]
        mid_point = sum(lengths) // len(lengths) // 2
        for row_index, row in enumerate(self.rows):
            new_row = []
            left_half = [character for character in row if character.input_coord.column <= mid_point]
            for character in left_half:
                character.motion.set_coordinate(Coord(character.input_coord.column, self.terminal.output_area.top))
                input_coord_path = character.motion.new_path(
                    speed=self.args.movement_speed, ease=self.args.movement_easing
                )
                input_coord_path.new_waypoint(character.input_coord)
                character.motion.activate_path(input_coord_path)
            opposite_row = self.rows[-(row_index + 1)]
            right_half = [c for c in opposite_row if c.input_coord.column > mid_point]
            for character in right_half:
                character.motion.set_coordinate(Coord(character.input_coord.column, self.terminal.output_area.bottom))
                input_coord_path = character.motion.new_path(
                    speed=self.args.movement_speed, ease=self.args.movement_easing
                )
                input_coord_path.new_waypoint(character.input_coord)
                character.motion.activate_path(input_coord_path)
            new_row.extend(left_half)
            new_row.extend(right_half)
            self.new_rows.append(new_row)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        while self.new_rows or self.active_chars:
            if self.new_rows:
                next_row = self.new_rows.pop(0)
                for character in next_row:
                    self.terminal.set_character_visibility(character, True)
                self.active_chars.extend(next_row)
            self.animate_chars()
            self.terminal.print()
            self.active_chars = [character for character in self.active_chars if character.is_active]

    def animate_chars(self) -> None:
        """Animates the characters by calling the move method and printing the characters to the terminal."""
        for character in self.active_chars:
            character.tick()
