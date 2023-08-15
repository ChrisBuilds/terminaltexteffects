import time
import terminaltexteffects.utils.terminaloperations as tops
from terminaltexteffects.effects import effect, effect_char
from enum import Enum, auto


class SlideDirection(Enum):
    UP = auto()
    DOWN = auto()


class ColumnSlide(effect.Effect):
    """Effect that slides each column into place."""

    def __init__(
        self, input_data: str, animation_rate: float = 0.003, SlideDirection: SlideDirection = SlideDirection.DOWN
    ):
        """Effect that slides each column into place.

        Args:
            input_data (str): string from stdin
            SlideDirection (SlideDirection, optional): Direction columns will slide. Defaults to SlideDirection.DOWN.
            animation_rate (float, optional): Delay between animation steps. Defaults to 0.001.
        """
        super().__init__(input_data, animation_rate)
        self.column_delay_distance: int = 2  # number of characters to wait before adding a new row
        self.slide_direction = SlideDirection

    def prepare_data(self) -> None:
        """Prepares the data for the effect by grouping the characters by column and setting the starting
        coordinate."""

        self.columns = self.input_by_column()
        if self.slide_direction == SlideDirection.DOWN:
            for column_list in self.columns.values():
                column_list.reverse()
        for column in self.columns.values():
            for character in column:
                if self.slide_direction == SlideDirection.DOWN:
                    character.current_coord.row = self.output_area.top
                else:
                    character.current_coord.row = self.output_area.bottom

    def get_next_column(self) -> list[effect_char.EffectCharacter]:
        """Gets the next column of characters to animate.

        Returns:
            list[effect_char.EffectCharacter]: The next column of characters to animate.
        """
        next_column = self.columns[min(self.columns.keys())]
        del self.columns[min(self.columns.keys())]
        return next_column

    def run(self) -> None:
        """Runs the effect."""
        self.prep_terminal()
        self.prepare_data()
        active_columns: list[list[effect_char.EffectCharacter]] = []
        active_columns.append(self.get_next_column())
        column_delay_countdown = self.column_delay_distance
        while active_columns or self.animating_chars or self.columns:
            if column_delay_countdown == 0 and self.columns:
                active_columns.append(self.get_next_column())
                column_delay_countdown = self.column_delay_distance
            else:
                if self.columns:
                    column_delay_countdown -= 1
            for column in active_columns:
                if column:
                    self.animating_chars.append(column.pop(0))
            self.animate_chars()

            # remove completed chars from animating chars
            self.animating_chars = [
                animating_char for animating_char in self.animating_chars if not animating_char.animation_completed()
            ]
            active_columns = [column for column in active_columns if column]

    def animate_chars(self) -> None:
        """Animates the characters by calling the tween method and printing the characters to the terminal."""
        for animating_char in self.animating_chars:
            tops.print_character(animating_char, clear_last=True)
            animating_char.move()
        time.sleep(self.animation_rate)
