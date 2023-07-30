import time
import utils.terminaloperations as tops
from effects import effect
import random


class ScatteredEffect(effect.Effect):
    """Effect that draws the characters into position from random starting locations."""

    def __init__(self, input_data: str):
        super().__init__(input_data)

    def prepare_data(self) -> None:
        """Prepares the data for the effect by scattering the characters within range of the input width and height."""
        for character in self.characters:
            character.current_coord.column = random.randint(1, self.input_width - 1)
            character.current_coord.row = random.randint(1, self.input_height - 1)
            self.animating_chars.append(character)

    def run(self, rate: float = 0) -> None:
        """Runs the effect.

        Args:
            rate (float, optional): Time to sleep between animation steps. Defaults to 0.
        """
        self.prep_terminal()
        self.prepare_data()
        while self.pending_chars or self.animating_chars:
            self.animate_chars(rate)
            self.completed_chars.extend(
                [completed_char for completed_char in self.animating_chars if completed_char.animation_completed()]
            )
            self.maintain_completed()
            self.animating_chars = [
                animating_char for animating_char in self.animating_chars if not animating_char.animation_completed()
            ]

    def animate_chars(self, rate: float) -> None:
        for animating_char in self.animating_chars:
            tops.print_character(animating_char, clear_last=True)
            animating_char.move()
        time.sleep(rate)
