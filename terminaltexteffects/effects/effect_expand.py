import time
import terminaltexteffects.utils.terminaloperations as tops
from terminaltexteffects import base_effect


class ExpandEffect(base_effect.Effect):
    """Effect that draws the characters expanding from a single point."""

    def __init__(self, input_data: str, animation_rate: float = 0.01):
        super().__init__(input_data, animation_rate)

    def prepare_data(self) -> None:
        """Prepares the data for the effect by starting all of the characters from a point in the middle of the input data."""

        for character in self.characters:
            character.current_coord.column = self.output_area.right // 2
            character.current_coord.row = self.output_area.top // 2
            self.animating_chars.append(character)

    def run(self) -> None:
        """Runs the effect."""
        self.prep_terminal()
        self.prepare_data()
        while self.animating_chars:
            self.animate_chars()
            self.completed_chars.extend(
                [animating_char for animating_char in self.animating_chars if animating_char.animation_completed()]
            )
            self.maintain_completed()
            self.animating_chars = [
                animating for animating in self.animating_chars if not animating.animation_completed()
            ]

    def animate_chars(self) -> None:
        for animating_char in self.animating_chars:
            tops.print_character(animating_char, clear_last=True)
            animating_char.move()
        time.sleep(self.animation_rate)
