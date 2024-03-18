import argparse
import typing
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils import easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.terminal import Terminal


@argclass(
    name="namedeffect",
    formatter_class=arg_validators.CustomFormatter,
    help="effect_description",
    description="effect_description",
    epilog=f"""{arg_validators.EASING_EPILOG}
    """,
)
@dataclass
class NamedEffectArgs(ArgsDataClass):
    color_single: graphics.Color = ArgField(
        cmd_name=["--color-single"],
        type_parser=arg_validators.Color.type_parser,
        default=0,
        metavar=arg_validators.Color.METAVAR,
        help="Color for the ___.",
    )  # type: ignore[assignment]
    color_list: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--color-list"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=0,
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the ___.",
    )  # type: ignore[assignment]
    final_color: graphics.Color = ArgField(
        cmd_name=["--final-color"],
        type_parser=arg_validators.Color.type_parser,
        default="ffffff",
        metavar=arg_validators.Color.METAVAR,
        help="Color for the final character.",
    )  # type: ignore[assignment]
    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("8A008A", "00D1FF", "FFFFFF"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=arg_validators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    final_gradient_frames: int = ArgField(
        cmd_name="--final-gradient-frames",
        type_parser=arg_validators.PositiveInt.type_parser,
        default=5,
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step.",
    )  # type: ignore[assignment]
    movement_speed: float = ArgField(
        cmd_name="--movement-speed",
        type_parser=arg_validators.PositiveFloat.type_parser,
        default=1,
        metavar=arg_validators.PositiveFloat.METAVAR,
        help="Speed of the ___.",
    )  # type: ignore[assignment]
    easing: typing.Callable = ArgField(
        cmd_name=["--easing"],
        default=easing.in_out_sine,
        type_parser=arg_validators.Ease.type_parser,
        help="Easing function to use for character movement.",
    )  # type: ignore[assignment]

    @classmethod
    def get_effect_class(cls):
        return NamedEffect


class NamedEffect:
    """Effect that ___."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def prepare_data(self) -> None:
        final_gradient = graphics.Gradient(self.args.final_gradient_stops, self.args.final_gradient_steps)
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient.get_color_at_fraction(
                character.input_coord.row / self.terminal.output_area.top
            )

            # do something with the data if needed (sort, adjust positions, etc)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        while self.pending_chars or self.active_chars:
            self.terminal.print()
            self.animate_chars()

            self.active_chars = [character for character in self.active_chars if character.is_active]

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method on all active characters."""
        for character in self.active_chars:
            character.tick()
