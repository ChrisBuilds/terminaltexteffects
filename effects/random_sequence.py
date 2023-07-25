import random
import time
import utils.terminaloperations as tops
from effects import base_effect


class RandomSequence(base_effect.Effect):
    """Prints the input data in a random sequence."""

    def __init__(self, input_data: str):
        super().__init__(input_data)

    def run(self, rate: float = 0) -> None:
        """Runs the effect.

        Args:
            rate (float, optional): Time to sleep between animation steps. Defaults to 0.
        """
        self.prep_terminal()
        random.shuffle(self.characters)
        for character in self.characters:
            tops.print_character_at_relative_position(character.symbol, character.x, character.y)
            time.sleep(rate)
