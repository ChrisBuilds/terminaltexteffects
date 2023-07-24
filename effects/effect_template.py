import time
import utils.terminaloperations as tops
from effects import base_effect


class NamedEffect(base_effect.Effect):
    """Effect that ___."""

    def __init__(self, input_data: str):
        super().__init__(input_data)

    def prepare_data(self) -> None:
        """Prepares the data for the effect by ___."""

        for character in self.characters:
            pass
            # do something with the data if needed (sort, adjust positions, etc)

    def run(self, rate: float = 0) -> None:
        """Runs the effect.

        Args:
            rate (float, optional): Time to sleep between animation steps. Defaults to 0.
        """
        self.prep_terminal()
        self.prepare_data()
        while self.pending_chars or self.animating_chars:
            self.animate_chars(rate)

            # tracking completed chars (remove if unnecessary)
            self.completed_chars.extend(
                [
                    animating_char
                    for animating_char in self.animating_chars
                    if animating_char.last_x == animating_char.target_x
                    and animating_char.last_y == animating_char.target_y
                ]
            )
            self.maintain_completed()

            # remove completed chars from animating chars
            self.animating_chars = [
                animating
                for animating in self.animating_chars
                if animating.last_x != animating.target_x or animating.last_y != animating.target_y
            ]

    def animate_chars(self, rate: float) -> None:
        """Animates the characters by calling the tween method and printing the characters to the terminal.

        Args:
            rate (float): time to sleep between animation steps
        """
        for animating_char in self.animating_chars:
            tops.print_character_at_relative_position(
                animating_char.character, animating_char.current_x, animating_char.current_y
            )
            if animating_char.last_x and animating_char.last_y:
                tops.print_character_at_relative_position(" ", animating_char.last_x, animating_char.last_y)
            animating_char.tween()
        time.sleep(rate)
