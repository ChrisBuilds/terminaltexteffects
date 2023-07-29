import time
import utils.terminaloperations as tops
from effects import effect


class ExpandEffect(effect.Effect):
    """Effect that draws the characters expanding from a single point."""

    def __init__(self, input_data: str):
        super().__init__(input_data)

    def prepare_data(self) -> None:
        """Prepares the data for the effect by starting all of the characters from a point in the middle of the input data."""

        for character in self.characters:
            character.current_coord.column = self.input_width // 2
            character.current_coord.row = self.output_area_top // 2
            self.animating_chars.append(character)

    def run(self, rate: float = 0) -> None:
        """Runs the effect.

        Args:
            rate (float, optional): Time to sleep between animation steps. Defaults to 0.
        """
        self.prep_terminal()
        self.prepare_data()
        while self.animating_chars:
            self.animate_chars(rate)
            self.completed_chars.extend(
                [animating_char for animating_char in self.animating_chars if animating_char.animation_completed()]
            )
            self.maintain_completed()
            self.animating_chars = [
                animating for animating in self.animating_chars if not animating.animation_completed()
            ]

    def animate_chars(self, rate: float) -> None:
        for animating_char in self.animating_chars:
            tops.print_character(animating_char, clear_last=True)
            animating_char.move()
        time.sleep(rate)
