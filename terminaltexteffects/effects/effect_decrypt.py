import time
import random
import terminaltexteffects.utils.terminaloperations as tops
from terminaltexteffects.effects import effect, effect_char
from dataclasses import dataclass

CIPHERTEXT_COLOR = 40
PLAINTEXT_COLOR = 208


@dataclass
class DecryptChars:
    """Various decimal utf-8 character ranges."""

    keyboard = list(range(33, 127))
    blocks = list(range(9608, 9632))
    box_drawing = list(range(9472, 9599))
    misc = list(range(174, 452))


class DecryptEffect(effect.Effect):
    """Effect that shows a movie style text decryption effect."""

    def __init__(self, input_data: str, animation_rate: float = 0.003):
        super().__init__(input_data, animation_rate)
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

    def make_decrypting_animation_units(self) -> list[effect_char.AnimationUnit]:
        animation_units = []
        graphicaleffect = effect_char.GraphicalEffect(color=CIPHERTEXT_COLOR)
        for _ in range(80):
            symbol = random.choice(self.encrypted_symbols)
            duration = 3
            animation_units.append(effect_char.AnimationUnit(symbol, duration, False, graphicaleffect))
        for n in range(random.randint(1, 15)):  # 1-15 longer duration units
            symbol = random.choice(self.encrypted_symbols)
            if random.randint(0, 100) <= 30:  # 30% chance of extra long duration
                duration = random.randrange(75, 225)  # wide long duration range reduces 'waves' in the animation
            else:
                duration = random.randrange(5, 10)  # shorter duration creates flipping effect
            animation_units.append(effect_char.AnimationUnit(symbol, duration, False, graphicaleffect))
        return animation_units

    def prepare_data_for_type_effect(self) -> None:
        """Prepares the data for the effect by building the animation for each character."""

        for character in self.characters:
            graphicaleffect = effect_char.GraphicalEffect(color=CIPHERTEXT_COLOR)
            character.animation_units.append(effect_char.AnimationUnit(chr(int("2588", 16)), 2, False, graphicaleffect))
            character.animation_units.append(effect_char.AnimationUnit(chr(int("2593", 16)), 2, False, graphicaleffect))
            character.animation_units.append(effect_char.AnimationUnit(chr(int("2592", 16)), 2, False, graphicaleffect))
            character.animation_units.append(effect_char.AnimationUnit(chr(int("2591", 16)), 2, False, graphicaleffect))
            character.final_graphical_effect = graphicaleffect
            character.alternate_symbol = random.choice(self.encrypted_symbols)
            character.use_alternate_symbol = True
            self.pending_chars.append(character)

    def prepare_data_for_decrypt_effect(self) -> None:
        """Prepares the data for the effect by building the animation for each character."""
        for character in self.characters:
            character.animation_units.extend(self.make_decrypting_animation_units())
            character.use_alternate_symbol = False
            character.final_graphical_effect.color = PLAINTEXT_COLOR
            self.animating_chars.append(character)

    def run(self) -> None:
        """Runs the effect."""
        self.prep_terminal()
        self.prepare_data_for_type_effect()
        self.run_type_effect()
        self.prepare_data_for_decrypt_effect()
        self.run_decryption_effect()

    def run_type_effect(self) -> None:
        """Runs the typing out the characters effect."""
        while self.pending_chars or self.animating_chars:
            if self.pending_chars:
                if random.randint(0, 100) <= 75:
                    self.animating_chars.append(self.pending_chars.pop(0))
            self.animate_chars()

            # remove completed chars from animating chars
            self.animating_chars = [
                animating_char for animating_char in self.animating_chars if not animating_char.animation_completed()
            ]

    def run_decryption_effect(self) -> None:
        while self.animating_chars:
            self.animate_chars()

            self.animating_chars = [
                animating_char for animating_char in self.animating_chars if not animating_char.animation_completed()
            ]

    def animate_chars(self) -> None:
        """Animates the characters by calling the tween method and printing the characters to the terminal."""
        for animating_char in self.animating_chars:
            animating_char.step_animation()
            tops.print_character(animating_char, clear_last=False)
            animating_char.move()

        time.sleep(self.animation_rate)
