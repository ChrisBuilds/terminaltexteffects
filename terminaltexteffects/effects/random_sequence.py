import random
import time
import utils.terminaloperations as tops
from effects import effect


class RandomSequence(effect.Effect):
    """Prints the input data in a random sequence."""

    def __init__(self, input_data: str, animation_rate: float = 0.01):
        """Initializes the effect.

        Args:
            input_data (str): The input data.
        """
        super().__init__(input_data, animation_rate)

    def run(self) -> None:
        """Runs the effect."""
        self.prep_terminal()
        random.shuffle(self.characters)
        for character in self.characters:
            tops.print_character(character)
            time.sleep(self.animation_rate)
