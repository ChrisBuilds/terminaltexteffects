import random
import typing
from collections.abc import Iterator
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.base_effect import BaseEffect
from terminaltexteffects.utils import graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.terminal import Terminal, TerminalConfig


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return RandomSequence, EffectConfig


@argclass(
    name="randomsequence",
    help="Prints the input data in a random sequence.",
    description="randomsequence | Prints the input data in a random sequence.",
    epilog="Example: terminaltexteffects randomsequence --starting-color 000000 --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --final-gradient-frames 12 --speed 0.004",
)
@dataclass
class EffectConfig(ArgsDataClass):
    """Configuration for the RandomSequence effect.

    Attributes:
        starting_color (graphics.Color): Color of the characters at spawn.
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.
        final_gradient_frames (int): Number of frames to display each gradient step.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the gradient for the final color.
        speed (float): Speed of the animation as a percentage of the total number of characters to reveal in each tick.
    """

    starting_color: graphics.Color = ArgField(
        cmd_name=["--starting-color"],
        type_parser=arg_validators.Color.type_parser,
        default="000000",
        metavar=arg_validators.Color.METAVAR,
        help="Color of the characters at spawn.",
    )  # type: ignore[assignment]
    "graphics.Color : Color of the characters at spawn."
    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("8A008A", "00D1FF", "FFFFFF"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color."
    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name=["--final-gradient-steps"],
        type_parser=arg_validators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] : Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."
    final_gradient_frames: int = ArgField(
        cmd_name=["--final-gradient-frames"],
        type_parser=arg_validators.PositiveInt.type_parser,
        default=12,
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step.",
    )  # type: ignore[assignment]
    "int : Number of frames to display each gradient step."
    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=arg_validators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.VERTICAL,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the gradient for the final color.",
    )  # type: ignore[assignment]
    "graphics.Gradient.Direction : Direction of the gradient for the final color."
    speed: float = ArgField(
        cmd_name=["--speed"],
        type_parser=arg_validators.PositiveFloat.type_parser,
        default=0.004,
        metavar=arg_validators.PositiveFloat.METAVAR,
        help="Speed of the animation as a percentage of the total number of characters to reveal in each tick.",
    )  # type: ignore[assignment]
    "float : Speed of the animation as a percentage of the total number of characters to reveal in each tick."

    @classmethod
    def get_effect_class(cls):
        return RandomSequence


class RandomSequence(BaseEffect):
    """Prints the input data in a random sequence."""

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
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def build(self) -> None:
        self._pending_chars.clear()
        self._active_chars.clear()
        self._character_final_color_map.clear()
        final_gradient = graphics.Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.config.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self._character_final_color_map[character] = final_gradient_mapping[character.input_coord]
            self.terminal.set_character_visibility(character, False)
            gradient_scn = character.animation.new_scene()
            gradient = graphics.Gradient(
                self.config.starting_color, self._character_final_color_map[character], steps=7
            )
            gradient_scn.apply_gradient_to_symbols(gradient, character.input_symbol, self.config.final_gradient_frames)
            character.animation.activate_scene(gradient_scn)
            self._pending_chars.append(character)
        self._built = True

    @property
    def built(self) -> bool:
        """Returns True if the effect has been built."""
        return self._built

    def __iter__(self) -> Iterator[str]:
        """Runs the effect."""
        if not self._built:
            self.build()
        random.shuffle(self._pending_chars)
        characters_per_tick = max(int(self.config.speed * len(self.terminal._input_characters)), 1)
        while self._pending_chars or self._active_chars:
            for _ in range(characters_per_tick):
                if self._pending_chars:
                    next_char = self._pending_chars.pop()
                    self.terminal.set_character_visibility(next_char, True)
                    self._active_chars.append(next_char)
            self._animate_chars()
            yield self.terminal.get_formatted_output_string()

            self._active_chars = [character for character in self._active_chars if character.is_active]
        self._built = False

    def _animate_chars(self) -> None:
        """Animates the characters by calling the tick method."""
        for character in self._active_chars:
            character.tick()
