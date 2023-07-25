"""Creates a rain effect where characters fall from the top of the terminal."""

import time
import random
import utils.terminaloperations as tops
from effects import base_effect


class RainEffect(base_effect.Effect):
    """Creates a rain effect where characters fall from the top of the terminal."""

    def __init__(self, input_data: str):
        super().__init__(input_data)
        self.group_by_y = {}

    def prepare_data(self) -> None:
        """Prepares the data for the effect by setting all characters y position to the input height and sorting by target y."""

        for character in self.characters:
            self.pending_chars.append(
                base_effect.EffectCharacter(
                    character=character,
                    current_x=character.x,
                    current_y=min(self.input_height, self.terminal_height - 1),
                )
            )
        for character in sorted(self.pending_chars, key=lambda x: x.target_y):
            if character.target_y not in self.group_by_y:
                self.group_by_y[character.target_y] = []
            self.group_by_y[character.target_y].append(character)

    def run(self, rate: float = 0) -> None:
        """Runs the effect.

        Args:
            rate (float, optional): Time to sleep between animation steps. Defaults to 0.
        """
        self.prep_terminal()
        self.prepare_data()
        self.pending_chars.clear()
        while self.group_by_y or self.animating_chars or self.pending_chars:
            if not self.pending_chars and self.group_by_y:
                self.pending_chars.extend(self.group_by_y.pop(min(self.group_by_y.keys())))
            if self.pending_chars:
                for _ in range(random.randint(1, 3)):
                    if self.pending_chars:
                        self.animating_chars.append(
                            self.pending_chars.pop(random.randint(0, len(self.pending_chars) - 1))
                        )
                    else:
                        break
            self.animate_chars(rate)
            # tracking completed chars (remove if unnecessary)
            self.completed_chars.extend(
                [
                    animating_char
                    for animating_char in self.animating_chars
                    if animating_char.last_x == animating_char.target_x
                    and animating_char.last_y == animating_char.target_y
                ]
            )
            self.maintain_completed()

            # remove completed chars from animating chars
            self.animating_chars = [
                animating
                for animating in self.animating_chars
                if animating.last_x != animating.target_x or animating.last_y != animating.target_y
            ]

    def animate_chars(self, rate: float) -> None:
        """Animates the characters by calling the tween method and printing the characters to the terminal.

        Args:
            rate (float): time to sleep between animation steps
        """
        for animating_char in self.animating_chars:
            tops.print_character_at_relative_position(
                animating_char.character, animating_char.current_x, animating_char.current_y
            )
            if animating_char.last_x and animating_char.last_y:
                tops.print_character_at_relative_position(" ", animating_char.last_x, animating_char.last_y)
            animating_char.tween()
        time.sleep(rate)
