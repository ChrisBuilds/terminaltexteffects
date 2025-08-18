"""Prints the input data in a random sequence, one character at a time.

Classes:
    RandomSequence: Prints the input data in a random sequence.
    RandomSequenceConfig: Configuration for the RandomSequence effect.
    RandomSequenceIterator: Iterator for the RandomSequence effect. Does not normally need to be called directly.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from terminaltexteffects import Color, EffectCharacter, Gradient
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.argutils import ArgSpec, ParserSpec


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "randomsequence", RandomSequence, RandomSequenceConfig


@dataclass
class RandomSequenceConfig(BaseConfig):
    """Configuration for the RandomSequence effect.

    Attributes:
        starting_color (Color): Color of the characters at spawn.
        speed (float): Speed of the animation as a percentage of the total number of characters to reveal in each tick.
            Valid values are 0 < n <= 1.
        final_gradient_stops (tuple[Color, ...]): Tuple of colors for the final color gradient. If only one color is
            provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Tuple of the number of gradient steps to use. More steps will
            create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_frames (int): Number of frames to display each gradient step. Increase to slow down the
            gradient animation.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.

    """

    parser_spec: ParserSpec = ParserSpec(
        name="randomsequence",
        help="Prints the input data in a random sequence.",
        description="randomsequence | Prints the input data in a random sequence.",
        epilog=(
            "Example: terminaltexteffects randomsequence --starting-color 000000 --final-gradient-stops 8A008A 00D1FF "
            "FFFFFF --final-gradient-steps 12 --final-gradient-frames 12 --speed 0.004"
        ),
    )

    starting_color: Color = ArgSpec(
        name="--starting-color",
        type=argutils.ColorArg.type_parser,
        default=Color("000000"),
        metavar=argutils.ColorArg.METAVAR,
        help="Color of the characters at spawn.",
    )  # pyright: ignore[reportAssignmentType]
    "Color : Color of the characters at spawn."

    speed: float = ArgSpec(
        name="--speed",
        type=argutils.PositiveFloat.type_parser,
        default=0.004,
        metavar=argutils.PositiveFloat.METAVAR,
        help="Speed of the animation as a percentage of the total number of characters to reveal in each tick.",
    )  # pyright: ignore[reportAssignmentType]
    "float : Speed of the animation as a percentage of the total number of characters to reveal in each tick."

    final_gradient_stops: tuple[Color, ...] = ArgSpec(
        name="--final-gradient-stops",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        default=(Color("8A008A"), Color("00D1FF"), Color("FFFFFF")),
        metavar=argutils.ColorArg.METAVAR,
        help=(
            "Space separated, unquoted, list of colors for the character gradient (applied across the canvas). "
            "If only one color is provided, the characters will be displayed in that color."
        ),
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[Color, ...] : Tuple of colors for the final color gradient. "
        "If only one color is provided, the characters will be displayed in that color."
    )

    final_gradient_steps: tuple[int, ...] | int = ArgSpec(
        name="--final-gradient-steps",
        type=argutils.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argutils.PositiveInt.METAVAR,
        help=(
            "Space separated, unquoted, list of the number of gradient steps to use. "
            "More steps will create a smoother and longer gradient animation."
        ),
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. "
        "More steps will create a smoother and longer gradient animation."
    )

    final_gradient_frames: int = ArgSpec(
        name="--final-gradient-frames",
        type=argutils.PositiveInt.type_parser,
        default=12,
        metavar=argutils.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step. Increase to slow down the gradient animation.",
    )  # pyright: ignore[reportAssignmentType]
    "int : Number of frames to display each gradient step. Increase to slow down the gradient animation."

    final_gradient_direction: Gradient.Direction = ArgSpec(
        name="--final-gradient-direction",
        type=argutils.GradientDirection.type_parser,
        default=Gradient.Direction.VERTICAL,
        metavar=argutils.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # pyright: ignore[reportAssignmentType]
    "Gradient.Direction : Direction of the final gradient."


class RandomSequenceIterator(BaseEffectIterator[RandomSequenceConfig]):
    """Iterator for the RandomSequence effect."""

    def __init__(self, effect: RandomSequence) -> None:
        """Initialize the effect iterator.

        Args:
            effect (RandomSequence): The effect to use for the iterator.

        """
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.characters_per_tick = max(int(self.config.speed * len(self.terminal._input_characters)), 1)
        self.build()

    def build(self) -> None:
        """Build the initial state of the effect."""
        final_gradient = Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.text_bottom,
            self.terminal.canvas.text_top,
            self.terminal.canvas.text_left,
            self.terminal.canvas.text_right,
            self.config.final_gradient_direction,
        )
        for character in self.terminal.get_characters():
            self.character_final_color_map[character] = final_gradient_mapping[character.input_coord]
            self.terminal.set_character_visibility(character, is_visible=False)
            gradient_scn = character.animation.new_scene()
            gradient = Gradient(self.config.starting_color, self.character_final_color_map[character], steps=7)
            gradient_scn.apply_gradient_to_symbols(
                character.input_symbol,
                self.config.final_gradient_frames,
                fg_gradient=gradient,
            )
            character.animation.activate_scene(gradient_scn)
            self.pending_chars.append(character)
        random.shuffle(self.pending_chars)

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        if self.pending_chars or self.active_characters:
            for _ in range(self.characters_per_tick):
                if self.pending_chars:
                    next_char = self.pending_chars.pop()
                    self.terminal.set_character_visibility(next_char, is_visible=True)
                    self.active_characters.add(next_char)
            self.update()
            return self.frame
        raise StopIteration


class RandomSequence(BaseEffect[RandomSequenceConfig]):
    """Prints the input data in a random sequence, one character at a time.

    Attributes:
        effect_config (PourConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    @property
    def _config_cls(self) -> type[RandomSequenceConfig]:
        return RandomSequenceConfig

    @property
    def _iterator_cls(self) -> type[RandomSequenceIterator]:
        return RandomSequenceIterator
