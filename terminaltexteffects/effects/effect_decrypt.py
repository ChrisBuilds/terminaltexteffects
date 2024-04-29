"""Movie style text decryption effect.

Classes:
    Decrypt: Movie style text decryption effect.
    DecryptConfig: Configuration for the Decrypt effect.
    DecryptIterator: Iterates over the Decrypt effect. Does not normally need to be called directly.
"""

import random
import typing
from dataclasses import dataclass

from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import animation, arg_validators, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return Decrypt, DecryptConfig


@argclass(
    name="decrypt",
    help="Display a movie style decryption effect.",
    description="decrypt | Movie style decryption effect.",
    epilog="Example: terminaltexteffects decrypt --typing-speed 2 --ciphertext-colors 008000 00cb00 00ff00 --final-gradient-stops eda000 --final-gradient-steps 12 --final-gradient-direction vertical",
)
@dataclass
class DecryptConfig(ArgsDataClass):
    """Configuration for the Decrypt effect.

    Attributes:
        typing_speed (int): Number of characters typed per keystroke.
        ciphertext_colors (tuple[graphics.Color, ...]): Colors for the ciphertext. Color will be randomly selected for each character.
        final_gradient_stops (tuple[graphics.Color, ...]): Colors for the character gradient. If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Number of gradient steps to use. More steps will create a smoother and longer gradient animation.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the final gradient."""

    typing_speed: int = ArgField(
        cmd_name="--typing-speed",
        type_parser=arg_validators.PositiveInt.type_parser,
        default=1,
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Number of characters typed per keystroke.",
    )  # type: ignore[assignment]
    "int : Number of characters typed per keystroke."

    ciphertext_colors: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--ciphertext-colors"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("008000", "00cb00", "00ff00"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the ciphertext. Color will be randomly selected for each character.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Colors for the ciphertext. Color will be randomly selected for each character."

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("eda000",),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Colors for the character gradient. If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=arg_validators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] : Number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=arg_validators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.VERTICAL,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "graphics.Gradient.Direction : Direction of the final gradient."

    @classmethod
    def get_effect_class(cls):
        return Decrypt


class DecryptIterator(BaseEffectIterator[DecryptConfig]):
    @dataclass
    class _DecryptChars:
        keyboard = list(range(33, 127))
        blocks = list(range(9608, 9632))
        box_drawing = list(range(9472, 9599))
        misc = list(range(174, 452))

    def __init__(self, effect: "Decrypt") -> None:
        super().__init__(effect)
        self._pending_chars: list[EffectCharacter] = []
        self._typing_pending_chars: list[EffectCharacter] = []
        self._decrypting_pending_chars: list[EffectCharacter] = []
        self._phase = "typing"
        self._active_chars: list[EffectCharacter] = []
        self._encrypted_symbols: list[str] = []
        self._scenes: dict[str, animation.Scene] = {}
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}
        self._make_encrypted_symbols()
        self._build()

    def _make_encrypted_symbols(self) -> None:
        for n in DecryptIterator._DecryptChars.keyboard:
            self._encrypted_symbols.append(chr(n))
        for n in DecryptIterator._DecryptChars.blocks:
            self._encrypted_symbols.append(chr(n))
        for n in DecryptIterator._DecryptChars.box_drawing:
            self._encrypted_symbols.append(chr(n))
        for n in DecryptIterator._DecryptChars.misc:
            self._encrypted_symbols.append(chr(n))

    def _make_decrypting_animation_scenes(self, character: EffectCharacter) -> None:
        fast_decrypt_scene = character.animation.new_scene(id="fast_decrypt")
        color = random.choice(self._config.ciphertext_colors)
        for _ in range(80):
            symbol = random.choice(self._encrypted_symbols)
            fast_decrypt_scene.add_frame(symbol, 3, color=color)
            duration = 3
        slow_decrypt_scene = character.animation.new_scene(id="slow_decrypt")
        for _ in range(random.randint(1, 15)):  # 1-15 longer duration units
            symbol = random.choice(self._encrypted_symbols)
            if random.randint(0, 100) <= 30:  # 30% chance of extra long duration
                duration = random.randrange(50, 125)  # wide long duration range reduces 'waves' in the animation
            else:
                duration = random.randrange(5, 10)  # shorter duration creates flipping effect
            slow_decrypt_scene.add_frame(symbol, duration, color=color)
        discovered_scene = character.animation.new_scene(id="discovered")
        discovered_gradient = graphics.Gradient("ffffff", self._character_final_color_map[character], steps=10)
        discovered_scene.apply_gradient_to_symbols(discovered_gradient, character.input_symbol, 8)

    def _prepare_data_for_type_effect(self) -> None:
        for character in self._terminal.get_characters():
            typing_scene = character.animation.new_scene(id="typing")
            for block_char in ["▉", "▓", "▒", "░"]:
                typing_scene.add_frame(block_char, 2, color=random.choice(self._config.ciphertext_colors))

            typing_scene.add_frame(
                random.choice(self._encrypted_symbols), 2, color=random.choice(self._config.ciphertext_colors)
            )
            self._typing_pending_chars.append(character)

    def _prepare_data_for_decrypt_effect(self) -> None:
        for character in self._terminal.get_characters():
            self._make_decrypting_animation_scenes(character)
            character.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE,
                character.animation.query_scene("fast_decrypt"),
                EventHandler.Action.ACTIVATE_SCENE,
                character.animation.query_scene("slow_decrypt"),
            )
            character.event_handler.register_event(
                EventHandler.Event.SCENE_COMPLETE,
                character.animation.query_scene("slow_decrypt"),
                EventHandler.Action.ACTIVATE_SCENE,
                character.animation.query_scene("discovered"),
            )
            character.animation.activate_scene(character.animation.query_scene("fast_decrypt"))
            self._decrypting_pending_chars.append(character)

    def _build(self) -> None:
        final_gradient = graphics.Gradient(*self._config.final_gradient_stops, steps=self._config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self._terminal.output_area.top, self._terminal.output_area.right, self._config.final_gradient_direction
        )
        for character in self._terminal.get_characters():
            self._character_final_color_map[character] = final_gradient_mapping[character.input_coord]
        self._prepare_data_for_type_effect()
        self._prepare_data_for_decrypt_effect()

    def __next__(self) -> str:
        if self._phase == "typing":
            if self._typing_pending_chars or self._active_chars:
                if self._typing_pending_chars:
                    if random.randint(0, 100) <= 75:
                        for _ in range(self._config.typing_speed):
                            if self._typing_pending_chars:
                                next_character = self._typing_pending_chars.pop(0)
                                self._terminal.set_character_visibility(next_character, True)
                                next_character.animation.activate_scene(next_character.animation.query_scene("typing"))
                                self._active_chars.append(next_character)
                for character in self._active_chars:
                    character.tick()
                self._active_chars = [character for character in self._active_chars if character.is_active]
                return self._terminal.get_formatted_output_string()
            else:
                self._active_chars = self._decrypting_pending_chars
                for char in self._active_chars:
                    char.animation.activate_scene(char.animation.query_scene("fast_decrypt"))
                self._phase = "decrypting"

        if self._phase == "decrypting":
            if self._active_chars:
                for character in self._active_chars:
                    character.tick()
                self._active_chars = [character for character in self._active_chars if character.is_active]
                return self._terminal.get_formatted_output_string()
            else:
                raise StopIteration
        else:
            raise StopIteration


class Decrypt(BaseEffect[DecryptConfig]):
    """Movie style text decryption effect.

    Attributes:
        effect_config (DecryptConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.

    """

    _config_cls = DecryptConfig
    _iterator_cls = DecryptIterator

    def __init__(self, input_data: str) -> None:
        """Initialize the effect with the provided input data.

        Args:
            input_data (str): The input data to use for the effect."""
        super().__init__(input_data)

    def __iter__(self) -> DecryptIterator:
        return DecryptIterator(self)
