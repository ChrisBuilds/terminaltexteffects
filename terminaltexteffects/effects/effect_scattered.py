import time
import terminaltexteffects.utils.terminaloperations as tops
from terminaltexteffects import base_effect
import random


class ScatteredEffect(base_effect.Effect):
    """Effect that draws the characters into position from random starting locations."""

    def __init__(self, input_data: str, animation_rate: float = 0.01):
        super().__init__(input_data, animation_rate)

    def prepare_data(self) -> None:
        """Prepares the data for the effect by scattering the characters within range of the input width and height."""
        for character in self.characters:
            character.current_coord.column = random.randint(1, self.output_area.right - 1)
            character.current_coord.row = random.randint(1, self.input_height - 1)
            character.graphical_effect.dim = True
            self.animating_chars.append(character)

    def run(self) -> None:
        """Runs the effect."""
        self.prep_terminal()
        self.prepare_data()
        while self.pending_chars or self.animating_chars:
            self.animate_chars()
            self.completed_chars.extend(
                [completed_char for completed_char in self.animating_chars if completed_char.animation_completed()]
            )
            self.maintain_completed()
            self.animating_chars = [
                animating_char for animating_char in self.animating_chars if not animating_char.animation_completed()
            ]

    def animate_chars(self) -> None:
        for animating_char in self.animating_chars:
            if animating_char.current_coord == animating_char.input_coord:
                animating_char.graphical_effect.disable_modes()
            tops.print_character(animating_char, clear_last=True)
            animating_char.move()
        time.sleep(self.animation_rate)
