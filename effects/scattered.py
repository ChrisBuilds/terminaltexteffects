import time
import utils.terminaloperations as tops
from effects import base_effect
import random


class ScatteredEffect(base_effect.Effect):
    """Effect that draws the characters into position from random starting locations."""

    def __init__(self, input_data: str):
        super().__init__(input_data)

    def prepare_data(self) -> None:
        """Prepares the data for the effect by scattering the characters within range of the input width and height."""
        for character in self.characters:
            self.animating_chars.append(
                base_effect.EffectCharacter(
                    character=character,
                    current_x=random.randint(1, self.input_width - 1),
                    current_y=random.randint(1, self.input_height - 1),
                )
            )

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
                [
                    completed_char
                    for completed_char in self.animating_chars
                    if completed_char.last_x == completed_char.target_x
                    and completed_char.last_y == completed_char.target_y
                ]
            )
            self.maintain_completed()
            self.animating_chars = [
                animating_char
                for animating_char in self.animating_chars
                if animating_char.last_x != animating_char.target_x or animating_char.last_y != animating_char.target_y
            ]

    def animate_chars(self, rate: float) -> None:
        for animating_char in self.animating_chars:
            tops.print_character_at_relative_position(
                animating_char.character, animating_char.current_x, animating_char.current_y
            )
            if animating_char.last_x and animating_char.last_y:
                tops.print_character_at_relative_position(" ", animating_char.last_x, animating_char.last_y)
            animating_char.tween()
        time.sleep(rate)
