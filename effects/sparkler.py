"""Effect that draws the characters spawning at varying rates from a single point."""

import time
import random
import utils.terminaloperations as tops
from effects import base_effect
from enum import Enum, auto


class SparklerPosition(Enum):
    """Position for the sparkler origin."""

    N = auto()
    NE = auto()
    E = auto()
    SE = auto()
    S = auto()
    SW = auto()
    W = auto()
    NW = auto()
    CENTER = auto()


class SparklerEffect(base_effect.Effect):
    """Effect that draws the characters spawning at varying rates from a single point."""

    def __init__(self, input_data: str, sparkler_position: SparklerPosition = SparklerPosition.CENTER):
        """Effect that draws the characters spawning at varying rates from a single point.

        Args:
            input_data (str): string from stdin
            sparkler_position (SparklerPosition, optional): Position for the sparkler origin. Defaults to SparklerPosition.CENTER.
        """
        super().__init__(input_data)
        self.sparkler_position = sparkler_position

    def prepare_data(self) -> None:
        """Prepares the data for the effect by starting all of the characters from a point based on SparklerPosition."""
        sparkler_origin_map = {
            SparklerPosition.CENTER: (self.input_width // 2, min(self.terminal_height // 2, self.input_height // 2)),
            SparklerPosition.N: (self.input_width // 2, min(self.terminal_height - 1, self.input_height - 1)),
            SparklerPosition.NW: (1, min(self.terminal_height - 1, self.input_height - 1)),
            SparklerPosition.W: (1, min(self.terminal_height // 2, self.input_height // 2)),
            SparklerPosition.SW: (1, 1),
            SparklerPosition.S: (self.input_width // 2, 1),
            SparklerPosition.SE: (self.input_width - 1, 1),
            SparklerPosition.E: (self.input_width - 1, min(self.terminal_height // 2, self.input_height // 2)),
            SparklerPosition.NE: (self.input_width - 1, min(self.terminal_height - 1, self.input_height - 1)),
        }

        for character in self.characters:
            current_x, current_y = sparkler_origin_map[self.sparkler_position]
            self.pending_chars.append(
                base_effect.EffectCharacter(
                    character=character,
                    current_x=current_x,
                    current_y=current_y,
                )
            )
        random.shuffle(self.pending_chars)

    def run(self, rate: float = 0) -> None:
        """Runs the effect.

        Args:
            rate (float, optional): Time to sleep between animation steps. Defaults to 0.
        """
        self.prep_terminal()
        self.prepare_data()
        while self.pending_chars or self.animating_chars:
            if self.pending_chars:
                for _ in range(random.randint(1, 5)):
                    if self.pending_chars:
                        self.animating_chars.append(self.pending_chars.pop())

            self.animate_chars(rate)
            self.completed_chars.extend(
                [
                    completed_char
                    for completed_char in self.animating_chars
                    if completed_char.last_x == completed_char.target_x
                    and completed_char.last_y == completed_char.target_y
                ]
            )
            self.maintain_completed()
            self.animating_chars = [
                animating_char
                for animating_char in self.animating_chars
                if animating_char.last_x != animating_char.target_x or animating_char.last_y != animating_char.target_y
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
