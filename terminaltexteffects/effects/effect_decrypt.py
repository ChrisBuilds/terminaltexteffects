import argparse
import random
from dataclasses import dataclass

from terminaltexteffects import base_character, base_effect
from terminaltexteffects.utils import graphics, argtypes
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
        type=argtypes.valid_animationrate,
        default=0.003,
        help="Time to sleep between animation steps. Defaults to 0.003 seconds.",
    )
    effect_parser.add_argument(
        "--ciphertext-color",
        type=argtypes.valid_color,
        default=40,
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the ciphertext. Defaults to 40",
    )
    effect_parser.add_argument(
        "--plaintext-color",
        type=argtypes.valid_color,
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


class DecryptEffect(base_effect.Effect):
    """Effect that shows a movie style text decryption effect."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        super().__init__(terminal, args)
        self.ciphertext_color = args.ciphertext_color
        self.plaintext_color = args.plaintext_color
        self.character_discovered_gradient = graphics.gradient("ffffff", self.plaintext_color, 5)
        self.encrypted_symbols: list[str] = []
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

    def make_decrypting_animation_scenes(self, character: base_character.EffectCharacter) -> None:
        for _ in range(80):
            symbol = random.choice(self.encrypted_symbols)
            duration = 3
            character.animator.add_effect_to_scene("fast_decrypt", symbol, self.ciphertext_color, duration)
        for _ in range(random.randint(1, 15)):  # 1-15 longer duration units
            symbol = random.choice(self.encrypted_symbols)
            if random.randint(0, 100) <= 30:  # 30% chance of extra long duration
                duration = random.randrange(75, 225)  # wide long duration range reduces 'waves' in the animation
            else:
                duration = random.randrange(5, 10)  # shorter duration creates flipping effect
            character.animator.add_effect_to_scene("slow_decrypt", symbol, self.ciphertext_color, duration)
        for color in self.character_discovered_gradient:
            character.animator.add_effect_to_scene("discovered", character.input_symbol, color, 20)

        character.animator.add_effect_to_scene("discovered", character.input_symbol, self.plaintext_color, 1)

    def prepare_data_for_type_effect(self) -> None:
        """Prepares the data for the effect by building the animation for each character."""
        for character in self.terminal.characters:
            for block_char in ["▉", "▓", "▒", "░"]:
                character.animator.add_effect_to_scene("typing", block_char, self.ciphertext_color, 2)
            character.animator.add_effect_to_scene(
                "typing", random.choice(self.encrypted_symbols), self.ciphertext_color, 2
            )
            self.pending_chars.append(character)

    def prepare_data_for_decrypt_effect(self) -> None:
        """Prepares the data for the effect by building the animation for each character."""
        for character in self.terminal.characters:
            self.make_decrypting_animation_scenes(character)
            character.event_handler.register_event(
                character.event_handler.Event.SCENE_COMPLETE,
                "fast_decrypt",
                character.event_handler.Action.ACTIVATE_SCENE,
                "slow_decrypt",
            )
            character.event_handler.register_event(
                character.event_handler.Event.SCENE_COMPLETE,
                "slow_decrypt",
                character.event_handler.Action.ACTIVATE_SCENE,
                "discovered",
            )
            character.animator.activate_scene("fast_decrypt")
            self.animating_chars.append(character)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data_for_type_effect()
        self.run_type_effect()
        self.prepare_data_for_decrypt_effect()
        self.run_decryption_effect()

    def run_type_effect(self) -> None:
        """Runs the typing out the characters effect."""
        self.terminal.print()
        while self.pending_chars or self.animating_chars:
            if self.pending_chars:
                if random.randint(0, 100) <= 75:
                    next_character = self.pending_chars.pop(0)
                    next_character.is_active = True
                    next_character.animator.activate_scene("typing")
                    self.animating_chars.append(next_character)
            self.animate_chars()
            # remove completed chars from animating chars
            self.animating_chars = [
                animating_char
                for animating_char in self.animating_chars
                if not animating_char.animator.is_active_scene_complete()
            ]
            self.terminal.print()

    def run_decryption_effect(self) -> None:
        while self.animating_chars:
            self.animate_chars()
            self.animating_chars = [
                animating_char
                for animating_char in self.animating_chars
                if not animating_char.animator.is_active_scene_complete()
            ]
            self.terminal.print()

    def animate_chars(self) -> None:
        """Animates the characters by calling the tween method and printing the characters to the terminal."""
        for animating_char in self.animating_chars:
            animating_char.animator.step_animation()
