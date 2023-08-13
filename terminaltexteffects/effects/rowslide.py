import time
import terminaltexteffects.utils.terminaloperations as tops
from terminaltexteffects.effects import effect, effect_char
from enum import Enum, auto


class SlideDirection(Enum):
    LEFT = auto()
    RIGHT = auto()


class RowSlide(effect.Effect):
    """Effect that slides each row into place."""

    def __init__(
        self, input_data: str, animation_rate: float = 0.003, SlideDirection: SlideDirection = SlideDirection.LEFT
    ):
        """Effect that slides each row into place.

        Args:
            input_data (str): string from stdin
            SlideDirection (SlideDirection, optional): Direction rows will slide. Defaults to SlideDirection.LEFT.
            animation_rate (float, optional): Delay between animation steps. Defaults to 0.001.
        """
        super().__init__(input_data, animation_rate)
        self.row_delay_distance: int = 8  # number of characters to wait before adding a new row
        self.slide_direction = SlideDirection

    def prepare_data(self) -> None:
        """Prepares the data for the effect by grouping the characters by row and setting the starting
        coordinate."""

        self.rows = self.input_by_row()
        self.rows.reverse()
        for row in self.rows:
            for character in row:
                if self.slide_direction == SlideDirection.LEFT:
                    character.current_coord.column = self.output_area.right
                else:
                    character.current_coord.column = 0

    def run(self) -> None:
        """Runs the effect."""
        self.prep_terminal()
        self.prepare_data()
        active_rows: list[list[effect_char.EffectCharacter]] = []
        active_rows.append(self.rows.pop(0))
        row_delay_countdown = self.row_delay_distance
        while active_rows or self.animating_chars:
            if row_delay_countdown == 0 and self.rows:
                active_rows.append(self.rows.pop(0))
                row_delay_countdown = self.row_delay_distance
            else:
                if self.rows:
                    row_delay_countdown -= 1
            for row in active_rows:
                if row:
                    if self.slide_direction == SlideDirection.LEFT:
                        self.animating_chars.append(row.pop(0))
                    else:
                        self.animating_chars.append(row.pop(-1))
            self.animate_chars()

            # remove completed chars from animating chars
            self.animating_chars = [
                animating_char for animating_char in self.animating_chars if not animating_char.animation_completed()
            ]
            active_rows = [row for row in active_rows if row]

    def animate_chars(self) -> None:
        """Animates the characters by calling the tween method and printing the characters to the terminal."""
        for animating_char in self.animating_chars:
            tops.print_character(animating_char, clear_last=True)
            animating_char.move()
        time.sleep(self.animation_rate)
