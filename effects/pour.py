"""Effect that pours the characters into position from the top, bottom, left, or right."""

import time
import utils.terminaloperations as tops
from effects import base_effect
from enum import Enum, auto


class PourDirection(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()


class PouringEffect(base_effect.Effect):
    """Effect that pours the characters into position from the top, bottom, left, or right."""

    def __init__(self, input_data: str, pour_direction: PourDirection = PourDirection.DOWN):
        super().__init__(input_data)
        self.pour_direction = pour_direction

    def prepare_data(self) -> None:
        """Prepares the data for the effect by sorting the characters by the pour direction."""
        sort_map = {
            PourDirection.DOWN: lambda character: character.y,
            PourDirection.UP: lambda character: -character.y,
            PourDirection.LEFT: lambda character: character.x,
            PourDirection.RIGHT: lambda character: -character.x,
        }
        self.characters.sort(key=sort_map[self.pour_direction])
        for character in self.characters:
            if self.pour_direction == PourDirection.DOWN:
                current_x = character.x
                current_y = min(self.terminal_height - 1, self.input_height)
            elif self.pour_direction == PourDirection.UP:
                current_x = character.x
                current_y = 0
            elif self.pour_direction == PourDirection.LEFT:
                current_x = self.terminal_width - 1
                current_y = character.y
            elif self.pour_direction == PourDirection.RIGHT:
                current_x = 0
                current_y = character.y
            self.pending_chars.append(
                base_effect.EffectCharacter(
                    character=character,
                    current_x=current_x,
                    current_y=current_y,
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
            if self.pending_chars:
                self.animating_chars.append(self.pending_chars.pop(0))
            self.animate_chars(rate)
            self.animating_chars = [
                animating_char
                for animating_char in self.animating_chars
                if animating_char.last_y != animating_char.target_y or animating_char.last_x != animating_char.target_x
            ]

    def animate_chars(self, rate: float) -> None:
        """Animates the sliding characters."""
        for animating_char in self.animating_chars:
            tops.print_character_at_relative_position(
                animating_char.character, animating_char.current_x, animating_char.current_y
            )
            if animating_char.last_x and animating_char.last_y:
                tops.print_character_at_relative_position(" ", animating_char.last_x, animating_char.last_y)
            animating_char.tween()

        time.sleep(rate)
