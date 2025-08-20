"""Movie style text decryption effect.

Classes:
    Decrypt: Movie style text decryption effect.
    DecryptConfig: Configuration for the Decrypt effect.
    DecryptIterator: Iterates over the Decrypt effect. Does not normally need to be called directly.
"""

from __future__ import annotations

import random
import typing
from dataclasses import dataclass

from terminaltexteffects import Color, ColorPair, EffectCharacter, EventHandler, Gradient, Scene
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.argutils import ArgSpec, ParserSpec


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Get the command, effect class, and configuration class for the effect.

    Returns:
        tuple[str, type[BaseEffect], type[BaseConfig]]: The command name, effect class, and configuration class.

    """
    return "decrypt", Decrypt, DecryptConfig


@dataclass
class DecryptConfig(BaseConfig):
    """Configuration for the Decrypt effect.

    Attributes:
        typing_speed (int): Number of characters typed per keystroke.
        ciphertext_colors (tuple[Color, ...]): Colors for the ciphertext. Color will be randomly selected for
            each character.
        final_gradient_stops (tuple[Color, ...]): Colors for the character gradient. If only one color is provided,
            the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...] | int): Number of gradient steps to use. More steps will create a
            smoother and longer gradient animation.
        final_gradient_direction (Gradient.Direction): Direction of the final gradient.

    """

    parser_spec: ParserSpec = ParserSpec(
        name="decrypt",
        help="Display a movie style decryption effect.",
        description="decrypt | Movie style decryption effect.",
        epilog=(
            "Example: terminaltexteffects decrypt --typing-speed 2 --ciphertext-colors 008000 00cb00 00ff00 "
            "--final-gradient-stops eda000 --final-gradient-steps 12 --final-gradient-direction vertical"
        ),
    )
    typing_speed: int = ArgSpec(
        name="--typing-speed",
        type=argutils.PositiveInt.type_parser,
        default=1,
        metavar=argutils.PositiveInt.METAVAR,
        help="Number of characters typed per keystroke.",
    )  # pyright: ignore[reportAssignmentType]
    "int : Number of characters typed per keystroke."

    ciphertext_colors: tuple[Color, ...] = ArgSpec(
        name="--ciphertext-colors",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        default=(Color("008000"), Color("00cb00"), Color("00ff00")),
        metavar=argutils.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the ciphertext. Color will be randomly selected for "
        "each character.",
    )  # pyright: ignore[reportAssignmentType]
    "tuple[Color, ...] : Colors for the ciphertext. Color will be randomly selected for each character."

    final_gradient_stops: tuple[Color, ...] = ArgSpec(
        name="--final-gradient-stops",
        type=argutils.ColorArg.type_parser,
        nargs="+",
        default=(Color("eda000"),),
        metavar=argutils.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied across the canvas). "
        "If only one color is provided, the characters will be displayed in that color.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[Color, ...] : Colors for the character gradient. If only one color is provided, the characters "
        "will be displayed in that color."
    )

    final_gradient_steps: tuple[int, ...] | int = ArgSpec(
        name="--final-gradient-steps",
        type=argutils.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argutils.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a "
        "smoother and longer gradient animation.",
    )  # pyright: ignore[reportAssignmentType]
    (
        "tuple[int, ...] | int : Number of gradient steps to use. More steps will create a smoother and "
        "longer gradient animation."
    )

    final_gradient_direction: Gradient.Direction = ArgSpec(
        name="--final-gradient-direction",
        type=argutils.GradientDirection.type_parser,
        default=Gradient.Direction.VERTICAL,
        metavar=argutils.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # pyright: ignore[reportAssignmentType]
    "Gradient.Direction : Direction of the final gradient."


class DecryptIterator(BaseEffectIterator[DecryptConfig]):
    """Iterator for the Decrypt effect."""

    @dataclass
    class _DecryptChars:
        keyboard: typing.ClassVar[list[int]] = list(range(33, 127))
        blocks: typing.ClassVar[list[int]] = list(range(9608, 9632))
        box_drawing: typing.ClassVar[list[int]] = list(range(9472, 9599))
        misc: typing.ClassVar[list[int]] = list(range(174, 452))

    def __init__(self, effect: Decrypt) -> None:
        """Initialize the iterator with the provided effect.

        Args:
            effect (Decrypt): The effect to use for the iterator.

        """
        super().__init__(effect)
        self.pending_chars: list[EffectCharacter] = []
        self.typing_pending_chars: list[EffectCharacter] = []
        self.decrypting_pending_chars: set[EffectCharacter] = set()
        self.phase = "typing"
        self.encrypted_symbols: list[str] = []
        self.scenes: dict[str, Scene] = {}
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.make_encrypted_symbols()
        self.build()

    def make_encrypted_symbols(self) -> None:
        """Create a list of encrypted symbols."""
        for n in DecryptIterator._DecryptChars.keyboard:
            self.encrypted_symbols.append(chr(n))
        for n in DecryptIterator._DecryptChars.blocks:
            self.encrypted_symbols.append(chr(n))
        for n in DecryptIterator._DecryptChars.box_drawing:
            self.encrypted_symbols.append(chr(n))
        for n in DecryptIterator._DecryptChars.misc:
            self.encrypted_symbols.append(chr(n))

    def make_decrypting_animation_scenes(self, character: EffectCharacter) -> None:
        """Create the animation scenes for decrypting the text."""
        fast_decrypt_scene = character.animation.new_scene(scene_id="fast_decrypt")
        color = random.choice(self.config.ciphertext_colors)
        for _ in range(80):
            symbol = random.choice(self.encrypted_symbols)
            fast_decrypt_scene.add_frame(symbol, 3, colors=ColorPair(fg=color))
            duration = 3
        slow_decrypt_scene = character.animation.new_scene(scene_id="slow_decrypt")
        for _ in range(random.randint(1, 15)):  # 1-15 longer duration units
            symbol = random.choice(self.encrypted_symbols)
            # 30% chance of extra long duration
            # wide duration range reduces 'waves' in the animation
            # shorter duration creates flipping effect
            duration = random.randrange(50, 125) if random.randint(0, 100) <= 30 else random.randrange(5, 10)
            slow_decrypt_scene.add_frame(symbol, duration, colors=ColorPair(fg=color))
        discovered_scene = character.animation.new_scene(scene_id="discovered")
        discovered_gradient = Gradient(Color("ffffff"), self.character_final_color_map[character], steps=10)
        discovered_scene.apply_gradient_to_symbols(character.input_symbol, 8, fg_gradient=discovered_gradient)

    def prepare_data_for_type_effect(self) -> None:
        """Prepare the data for the typing effect."""
        for character in self.terminal.get_characters():
            typing_scene = character.animation.new_scene(scene_id="typing")
            for block_char in ["▉", "▓", "▒", "░"]:
                typing_scene.add_frame(
                    block_char,
                    2,
                    colors=ColorPair(fg=random.choice(self.config.ciphertext_colors)),
                )

            typing_scene.add_frame(
                random.choice(self.encrypted_symbols),
                2,
                colors=ColorPair(fg=random.choice(self.config.ciphertext_colors)),
            )
            self.typing_pending_chars.append(character)

    def prepare_data_for_decrypt_effect(self) -> None:
        """Prepare the data for the decrypting effect."""
        for character in self.terminal.get_characters():
            self.make_decrypting_animation_scenes(character)
            character.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE,
                "fast_decrypt",
                EventHandler.Action.ACTIVATE_SCENE,
                "slow_decrypt",
            )
            character.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE,
                "slow_decrypt",
                EventHandler.Action.ACTIVATE_SCENE,
                "discovered",
            )
            character.animation.activate_scene("fast_decrypt")
            self.decrypting_pending_chars.add(character)

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
        self.prepare_data_for_type_effect()
        self.prepare_data_for_decrypt_effect()

    def __next__(self) -> str:
        """Return the next frame in the animation."""
        if self.phase == "typing":
            if self.typing_pending_chars or self.active_characters:
                if self.typing_pending_chars and random.randint(0, 100) <= 75:
                    for _ in range(self.config.typing_speed):
                        if self.typing_pending_chars:
                            next_character = self.typing_pending_chars.pop(0)
                            self.terminal.set_character_visibility(next_character, is_visible=True)
                            next_character.animation.activate_scene("typing")
                            self.active_characters.add(next_character)
                self.update()
                return self.frame
            self.active_characters = self.decrypting_pending_chars
            for char in self.active_characters:
                char.animation.activate_scene("fast_decrypt")
            self.phase = "decrypting"

        if self.phase == "decrypting":
            if self.active_characters:
                self.update()
                return self.frame
            raise StopIteration
        raise StopIteration


class Decrypt(BaseEffect[DecryptConfig]):
    """Movie style text decryption effect.

    Attributes:
        effect_config (DecryptConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    @property
    def _config_cls(self) -> type[DecryptConfig]:
        return DecryptConfig

    @property
    def _iterator_cls(self) -> type[DecryptIterator]:
        return DecryptIterator
