"""Effect that pours the characters into position from the top, bottom, left, or right."""

import time
import terminaltexteffects.utils.terminaloperations as tops
from terminaltexteffects import base_effect
from enum import Enum, auto


class PourDirection(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()


class PouringEffect(base_effect.Effect):
    """Effect that pours the characters into position from the top, bottom, left, or right."""

    def __init__(
        self, input_data: str, animation_rate: float = 0.004, pour_direction: PourDirection = PourDirection.DOWN
    ):
        super().__init__(input_data, animation_rate)
        self.pour_direction = pour_direction

    def prepare_data(self) -> None:
        """Prepares the data for the effect by sorting the characters by the pour direction."""
        sort_map = {
            PourDirection.DOWN: lambda character: character.input_coord.row,
            PourDirection.UP: lambda character: -character.input_coord.row,
            PourDirection.LEFT: lambda character: character.input_coord.column,
            PourDirection.RIGHT: lambda character: -character.input_coord.column,
        }
        self.characters.sort(key=sort_map[self.pour_direction])
        for character in self.characters:
            if self.pour_direction == PourDirection.DOWN:
                character.current_coord.column = character.input_coord.column
                character.current_coord.row = self.output_area.top
            elif self.pour_direction == PourDirection.UP:
                character.current_coord.column = character.input_coord.column
                character.current_coord.row = self.output_area.bottom
            elif self.pour_direction == PourDirection.LEFT:
                character.current_coord.column = self.output_area.right
                character.current_coord.row = character.input_coord.row
            elif self.pour_direction == PourDirection.RIGHT:
                character.current_coord.column = self.output_area.left
                character.current_coord.row = character.input_coord.row
            self.pending_chars.append(character)

    def run(self) -> None:
        """Runs the effect."""
        self.prep_terminal()
        self.prepare_data()
        while self.pending_chars or self.animating_chars:
            if self.pending_chars:
                self.animating_chars.append(self.pending_chars.pop(0))
            self.animate_chars()
            self.animating_chars = [
                animating_char for animating_char in self.animating_chars if not animating_char.animation_completed()
            ]

    def animate_chars(self) -> None:
        """Animates the sliding characters."""
        for animating_char in self.animating_chars:
            tops.print_character(animating_char, clear_last=True)
            animating_char.move()
        time.sleep(self.animation_rate)
