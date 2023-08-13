import time
import terminaltexteffects.utils.terminaloperations as tops
from terminaltexteffects.effects import effect


class VerticalSlice(effect.Effect):
    """Effect that slices the input in half vertically and slides it into place from opposite directions."""

    def __init__(self, input_data: str, animation_rate: float = 0.02):
        super().__init__(input_data, animation_rate)

    def prepare_data(self) -> None:
        """Prepares the data for the effect by setting the left half to start at the top and the
        right half to start at the bottom, and creating rows consisting off halves from opposite
        input rows."""

        self.rows = list(self.input_by_row().values())
        lengths = [max([c.input_coord.column for c in row]) for row in self.rows]
        mid_point = sum(lengths) // len(lengths) // 2
        self.new_rows = []
        for i, row in enumerate(self.rows):
            new_row = []
            left_half = [c for c in row if c.input_coord.column <= mid_point]
            for c in left_half:
                c.current_coord.row = self.output_area.top
            opposite_row = self.rows[-(i + 1)]
            right_half = [c for c in opposite_row if c.input_coord.column > mid_point]
            for c in right_half:
                c.current_coord.row = self.output_area.bottom
            new_row.extend(left_half)
            new_row.extend(right_half)
            self.new_rows.append(new_row)

    def run(self) -> None:
        """Runs the effect."""
        self.prep_terminal()
        self.prepare_data()
        while self.new_rows or self.animating_chars:
            if self.new_rows:
                self.animating_chars.extend(self.new_rows.pop(0))
            self.animate_chars()

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
