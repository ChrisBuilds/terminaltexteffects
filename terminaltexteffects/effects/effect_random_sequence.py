"""Prints the input data in a random sequence, one character at a time.

Classes:
    RandomSequence: Prints the input data in a random sequence.
    RandomSequenceConfig: Configuration for the RandomSequence effect.
    RandomSequenceIterator: Iterator for the RandomSequence effect. Does not normally need to be called directly.
"""

import random
import typing
from dataclasses import dataclass

import terminaltexteffects.utils.argvalidators as argvalidators
from terminaltexteffects.engine.base_character import EffectCharacter
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return RandomSequence, RandomSequenceConfig


@argclass(
    name="randomsequence",
    help="Prints the input data in a random sequence.",
    description="randomsequence | Prints the input data in a random sequence.",
    epilog="Example: terminaltexteffects randomsequence --starting-color 000000 --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --final-gradient-frames 12 --speed 0.004",
)
@dataclass
class RandomSequenceConfig(ArgsDataClass):
    """Configuration for the RandomSequence effect.

    Attributes:
        starting_color (graphics.Color): Color of the characters at spawn.
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_frames (int): Number of frames to display each gradient step.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the final gradient.
        speed (float): Speed of the animation as a percentage of the total number of characters to reveal in each tick. Valid values are 0 < n <= 1.
    """

    starting_color: graphics.Color = ArgField(
        cmd_name=["--starting-color"],
        type_parser=argvalidators.ColorArg.type_parser,
        default="000000",
        metavar=argvalidators.ColorArg.METAVAR,
        help="Color of the characters at spawn.",
    )  # type: ignore[assignment]

    "graphics.Color : Color of the characters at spawn."
    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=("8A008A", "00D1FF", "FFFFFF"),
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

    "tuple[int, ...] : Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."
    final_gradient_frames: int = ArgField(
        cmd_name=["--final-gradient-frames"],
        type_parser=argvalidators.PositiveInt.type_parser,
        default=12,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step.",
    )  # type: ignore[assignment]

    "int : Number of frames to display each gradient step."
    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.VERTICAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]

    "graphics.Gradient.Direction : Direction of the final gradient."
    speed: float = ArgField(
        cmd_name=["--speed"],
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=0.004,
        metavar=argvalidators.PositiveFloat.METAVAR,
        help="Speed of the animation as a percentage of the total number of characters to reveal in each tick.",
    )  # type: ignore[assignment]

    "float : Speed of the animation as a percentage of the total number of characters to reveal in each tick."

    @classmethod
    def get_effect_class(cls):
        return RandomSequence


class RandomSequenceIterator(BaseEffectIterator[RandomSequenceConfig]):
    def __init__(self, effect: "RandomSequence") -> None:
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.character_final_color_map: dict[EffectCharacter, graphics.Color] = {}
        self.characters_per_tick = max(int(self.config.speed * len(self.terminal._input_characters)), 1)
        self.build()

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
        random.shuffle(self.pending_chars)

    def __next__(self) -> str:
        if self.pending_chars or self.active_characters:
            for _ in range(self.characters_per_tick):
                if self.pending_chars:
                    next_char = self.pending_chars.pop()
                    self.terminal.set_character_visibility(next_char, True)
                    self.active_characters.append(next_char)
            self.update()
            return self.frame
        raise StopIteration


class RandomSequence(BaseEffect[RandomSequenceConfig]):
    """Prints the input data in a random sequence, one character at a time.

    Attributes:
        effect_config (PourConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.
    """

    _config_cls = RandomSequenceConfig
    _iterator_cls = RandomSequenceIterator

    def __init__(self, input_data: str) -> None:
        """Initialize the effect with the provided input data.

        Args:
            input_data (str): The input data to use for the effect."""
        super().__init__(input_data)
