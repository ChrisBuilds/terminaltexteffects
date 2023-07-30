import time
import utils.terminaloperations as tops
from effects import effect


class NamedEffect(effect.Effect):
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
                [animating_char for animating_char in self.animating_chars if animating_char.animation_completed()]
            )
            self.maintain_completed()

            # remove completed chars from animating chars
            self.animating_chars = [
                animating_char for animating_char in self.animating_chars if not animating_char.animation_completed()
            ]

    def animate_chars(self, rate: float) -> None:
        """Animates the characters by calling the tween method and printing the characters to the terminal.

        Args:
            rate (float): time to sleep between animation steps
        """
        for animating_char in self.animating_chars:
            tops.print_character(animating_char, clear_last=True)
            animating_char.move()
        time.sleep(rate)
