"""Effect that draws the characters spawning at varying rates from a single point."""

import time
import random
import terminaltexteffects.utils.terminaloperations as tops
from terminaltexteffects.effects import effect, effect_char
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


class SparklerEffect(effect.Effect):
    """Effect that draws the characters spawning at varying rates from a single point."""

    def __init__(
        self,
        input_data: str,
        animation_rate: float = 0.01,
        sparkler_position: SparklerPosition = SparklerPosition.CENTER,
    ):
        """Effect that draws the characters spawning at varying rates from a single point.

        Args:
            input_data (str): string from stdin
            sparkler_position (SparklerPosition, optional): Position for the sparkler origin. Defaults to SparklerPosition.CENTER.
        """
        super().__init__(input_data, animation_rate)
        self.sparkler_position = sparkler_position

    def prepare_data(self) -> None:
        """Prepares the data for the effect by starting all of the characters from a point based on SparklerPosition."""
        sparkler_origin_map = {
            SparklerPosition.CENTER: (
                self.output_area.right // 2,
                min(self.terminal_height // 2, self.input_height // 2),
            ),
            SparklerPosition.N: (self.output_area.right // 2, self.output_area.top),
            SparklerPosition.NW: (self.output_area.left, self.output_area.top),
            SparklerPosition.W: (self.output_area.left, min(self.terminal_height // 2, self.input_height // 2)),
            SparklerPosition.SW: (self.output_area.left, self.output_area.bottom),
            SparklerPosition.S: (self.output_area.right // 2, self.output_area.bottom),
            SparklerPosition.SE: (self.output_area.right - 1, self.output_area.bottom),
            SparklerPosition.E: (self.output_area.right - 1, min(self.terminal_height // 2, self.input_height // 2)),
            SparklerPosition.NE: (self.output_area.right - 1, self.output_area.top),
        }

        for character in self.characters:
            character.current_coord.column, character.current_coord.row = sparkler_origin_map[self.sparkler_position]
            white = effect_char.GraphicalEffect(color=231)
            yellow = effect_char.GraphicalEffect(color=11)
            orange = effect_char.GraphicalEffect(color=202)
            colors = [white, yellow, orange]
            random.shuffle(colors)
            character.animation_units.append(
                effect_char.AnimationUnit(character.symbol, random.randint(20, 35), False, colors.pop())
            )
            character.animation_units.append(
                effect_char.AnimationUnit(character.symbol, random.randint(20, 35), False, colors.pop())
            )
            character.animation_units.append(
                effect_char.AnimationUnit(character.symbol, random.randint(20, 35), False, colors.pop())
            )
            self.pending_chars.append(character)
        random.shuffle(self.pending_chars)

    def run(self) -> None:
        """Runs the effect."""
        self.prep_terminal()
        self.prepare_data()
        while self.pending_chars or self.animating_chars:
            if self.pending_chars:
                for _ in range(random.randint(1, 5)):
                    if self.pending_chars:
                        self.animating_chars.append(self.pending_chars.pop())

            self.animate_chars()
            self.completed_chars.extend(
                [completed_char for completed_char in self.animating_chars if completed_char.animation_completed()]
            )
            self.maintain_completed()
            self.animating_chars = [
                animating_char for animating_char in self.animating_chars if not animating_char.animation_completed()
            ]

    def animate_chars(self) -> None:
        for animating_char in self.animating_chars:
            animating_char.step_animation()
            tops.print_character(animating_char, clear_last=True)
            animating_char.move()
        time.sleep(self.animation_rate)
