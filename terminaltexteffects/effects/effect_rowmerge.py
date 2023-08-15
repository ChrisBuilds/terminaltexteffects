import time
import terminaltexteffects.utils.terminaloperations as tops
from terminaltexteffects.effects import effect


class RowMergeEffect(effect.Effect):
    """Effect that merges rows."""

    def __init__(self, input_data: str, animation_rate: float = 0.03):
        super().__init__(input_data, animation_rate)

    def prepare_data(self) -> None:
        """Prepares the data for the effect by setting every other row to start at the opposite
        side of the terminal and reverse the order."""

        self.rows = []
        for i, row in self.input_by_row().items():
            if i % 2 == 0:
                row = row[::-1]
                for c in row:
                    c.current_coord.column = self.output_area.left
            else:
                for c in row:
                    c.current_coord.column = self.output_area.right
            self.rows.append(row)

    def run(self) -> None:
        """Runs the effect."""
        self.prep_terminal()
        self.prepare_data()
        while self.rows or self.animating_chars:
            self.animate_chars()
            for row in self.rows:
                if row:
                    self.animating_chars.append(row.pop(0))
            self.rows = [row for row in self.rows if row]

            # remove completed chars from animating chars
            self.animating_chars = [
                animating_char for animating_char in self.animating_chars if not animating_char.animation_completed()
            ]

    def animate_chars(self) -> None:
        """Animates the characters by calling the move method and printing the characters to the terminal."""
        for animating_char in self.animating_chars:
            tops.print_character(animating_char, clear_last=True)
            animating_char.move()
        time.sleep(self.animation_rate)
