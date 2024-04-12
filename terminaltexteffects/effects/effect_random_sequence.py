import random
import typing
from collections.abc import Iterator
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils import exceptions, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.terminal import Terminal, TerminalConfig


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return RandomSequence, RandomSequenceConfig


@argclass(
    name="randomsequence",
    formatter_class=arg_validators.CustomFormatter,
    help="Prints the input data in a random sequence.",
    description="randomsequence | Prints the input data in a random sequence.",
    epilog="Example: terminaltexteffects randomsequence --starting-color 000000 --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --final-gradient-frames 12 --speed 0.004",
)
@dataclass
class RandomSequenceConfig(ArgsDataClass):
    starting_color: graphics.Color = ArgField(
        cmd_name=["--starting-color"],
        type_parser=arg_validators.Color.type_parser,
        default="000000",
        metavar=arg_validators.Color.METAVAR,
        help="Color of the characters at spawn.",
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
        cmd_name=["--final-gradient-steps"],
        type_parser=arg_validators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    final_gradient_frames: int = ArgField(
        cmd_name=["--final-gradient-frames"],
        type_parser=arg_validators.PositiveInt.type_parser,
        default=12,
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step.",
    )  # type: ignore[assignment]
    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=arg_validators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.VERTICAL,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the gradient for the final color.",
    )  # type: ignore[assignment]
    speed: float = ArgField(
        cmd_name=["--speed"],
        type_parser=arg_validators.PositiveFloat.type_parser,
        default=0.004,
        metavar=arg_validators.PositiveFloat.METAVAR,
        help="Speed of the animation as a percentage of the total number of characters.",
    )  # type: ignore[assignment]

    @classmethod
    def get_effect_class(cls):
        return RandomSequence


class RandomSequence:
    """Prints the input data in a random sequence."""

    def __init__(
        self,
        input_data: str,
        effect_config: RandomSequenceConfig = RandomSequenceConfig(),
        terminal_config: TerminalConfig = TerminalConfig(),
    ):
        """Initializes the effect.

        Args:
            terminal (Terminal): Terminal object.
            args (argparse.Namespace): Arguments from argparse.
        """
        self.terminal = Terminal(input_data, terminal_config)
        self.config = effect_config
        self.built = False
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def build(self) -> None:
        final_gradient = graphics.Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.config.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
            self.terminal.set_character_visibility(character, False)
            gradient_scn = character.animation.new_scene()
            gradient = graphics.Gradient(self.config.starting_color, self.character_final_color_map[character], steps=7)
            gradient_scn.apply_gradient_to_symbols(gradient, character.input_symbol, self.config.final_gradient_frames)
            character.animation.activate_scene(gradient_scn)
            self.pending_chars.append(character)
        self.built = True

    def __iter__(self) -> Iterator[str]:
        """Runs the effect."""
        if not self.built:
            raise exceptions.EffectNotBuiltError("Effect must be built before running.")
        random.shuffle(self.pending_chars)
        characters_per_tick = max(int(self.config.speed * len(self.terminal._input_characters)), 1)
        while self.pending_chars or self.active_chars:
            for _ in range(characters_per_tick):
                if self.pending_chars:
                    self.next_char = self.pending_chars.pop()
                    self.terminal.set_character_visibility(self.next_char, True)
                    self.active_chars.append(self.next_char)
            self.animate_chars()
            yield self.terminal.get_formatted_output_string()

            self.active_chars = [character for character in self.active_chars if character.is_active]

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method."""
        for character in self.active_chars:
            character.tick()
