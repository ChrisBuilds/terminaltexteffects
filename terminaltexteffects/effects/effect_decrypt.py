import argparse
import random
from dataclasses import dataclass

from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils import argtypes, graphics
from terminaltexteffects.utils.terminal import Terminal


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "decrypt",
        help="Display a movie style decryption effect.",
        description="decrypt | Movie style decryption effect.",
        epilog="Example: terminaltexteffects decrypt -a 0.003 --cipher-text-color 40 --plain-text-color 208",
    )
    effect_parser.set_defaults(effect_class=DecryptEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.nonnegative_float,
        default=0.003,
        help="Time to sleep between animation steps. Defaults to 0.003 seconds.",
    )
    effect_parser.add_argument(
        "--ciphertext-color",
        type=argtypes.color,
        default=40,
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the ciphertext. Defaults to 40",
    )
    effect_parser.add_argument(
        "--plaintext-color",
        type=argtypes.color,
        default="ffb007",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the plaintext. Defaults to 208.",
    )


@dataclass
class DecryptChars:
    """Various decimal utf-8 character ranges."""

    keyboard = list(range(33, 127))
    blocks = list(range(9608, 9632))
    box_drawing = list(range(9472, 9599))
    misc = list(range(174, 452))


class DecryptEffect:
    """Effect that shows a movie style text decryption effect."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.ciphertext_color = args.ciphertext_color
        self.plaintext_color = args.plaintext_color
        self.character_discovered_gradient: graphics.Gradient = graphics.Gradient(["ffffff", self.plaintext_color], 5)
        self.encrypted_symbols: list[str] = []
        self.scenes: dict[str, graphics.Scene] = {}
        self.make_encrypted_symbols()

    def make_encrypted_symbols(self) -> None:
        for n in DecryptChars.keyboard:
            self.encrypted_symbols.append(chr(n))
        for n in DecryptChars.blocks:
            self.encrypted_symbols.append(chr(n))
        for n in DecryptChars.box_drawing:
            self.encrypted_symbols.append(chr(n))
        for n in DecryptChars.misc:
            self.encrypted_symbols.append(chr(n))

    def make_decrypting_animation_scenes(self, character: EffectCharacter) -> None:
        fast_decrypt_scene = character.animation.new_scene(id="fast_decrypt")
        for _ in range(80):
            symbol = random.choice(self.encrypted_symbols)
            fast_decrypt_scene.add_frame(symbol, 3, color=self.ciphertext_color)
            duration = 3
        slow_decrypt_scene = character.animation.new_scene(id="slow_decrypt")
        for _ in range(random.randint(1, 15)):  # 1-15 longer duration units
            symbol = random.choice(self.encrypted_symbols)
            if random.randint(0, 100) <= 30:  # 30% chance of extra long duration
                duration = random.randrange(75, 225)  # wide long duration range reduces 'waves' in the animation
            else:
                duration = random.randrange(5, 10)  # shorter duration creates flipping effect
            slow_decrypt_scene.add_frame(symbol, duration, color=self.ciphertext_color)
        discovered_scene = character.animation.new_scene(id="discovered")
        for color in self.character_discovered_gradient:
            discovered_scene.add_frame(character.input_symbol, 20, color=color)

        discovered_scene.add_frame(character.input_symbol, 1, color=self.plaintext_color)

    def prepare_data_for_type_effect(self) -> None:
        """Prepares the data for the effect by building the animation for each character."""
        for character in self.terminal._input_characters:
            typing_scene = character.animation.new_scene(id="typing")
            for block_char in ["▉", "▓", "▒", "░"]:
                typing_scene.add_frame(block_char, 2, color=self.ciphertext_color)

            typing_scene.add_frame(random.choice(self.encrypted_symbols), 2, color=self.ciphertext_color)
            self.pending_chars.append(character)

    def prepare_data_for_decrypt_effect(self) -> None:
        """Prepares the data for the effect by building the animation for each character."""
        for character in self.terminal._input_characters:
            self.make_decrypting_animation_scenes(character)
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
            self.active_chars.append(character)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data_for_type_effect()
        self.run_type_effect()
        self.prepare_data_for_decrypt_effect()
        self.run_decryption_effect()

    def run_type_effect(self) -> None:
        """Runs the typing out the characters effect."""
        self.terminal.print()
        while self.pending_chars or self.active_chars:
            if self.pending_chars:
                if random.randint(0, 100) <= 75:
                    next_character = self.pending_chars.pop(0)
                    self.terminal.set_character_visibility(next_character, True)
                    next_character.animation.activate_scene(next_character.animation.query_scene("typing"))
                    self.active_chars.append(next_character)
            self.animate_chars()
            self.active_chars = [character for character in self.active_chars if character.is_active]
            self.terminal.print()

    def run_decryption_effect(self) -> None:
        while self.active_chars:
            self.animate_chars()
            self.active_chars = [character for character in self.active_chars if character.is_active]
            self.terminal.print()

    def animate_chars(self) -> None:
        """Animates the characters by calling the tween method and printing the characters to the terminal."""
        for character in self.active_chars:
            character.tick()
