import time
import utils.terminaloperations as tops
from effects import base_effect


class ExpandEffect(base_effect.Effect):
    """Effect that draws the characters expanding from a single point."""

    def __init__(self, input_data: str):
        super().__init__(input_data)

    def prepare_data(self) -> None:
        """Prepares the data for the effect by starting all of the characters from a point in the middle of the input data."""

        for character in self.characters:
            self.animating_chars.append(
                base_effect.EffectCharacter(
                    character=character,
                    current_x=self.input_width // 2,
                    current_y=min(self.terminal_height // 2, self.input_height // 2),
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
                    animating_char
                    for animating_char in self.animating_chars
                    if animating_char.last_x == animating_char.target_x
                    and animating_char.last_y == animating_char.target_y
                ]
            )
            self.maintain_completed()
            self.animating_chars = [
                animating
                for animating in self.animating_chars
                if animating.last_x != animating.target_x or animating.last_y != animating.target_y
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
