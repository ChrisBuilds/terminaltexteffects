import time
import random
import utils.terminaloperations as tops
from effects import effect, effect_char


class ShootingStarEffect(effect.Effect):
    """Effect that display the text as a falling star toward the final coordinate of the character."""

    def __init__(self, input_data: str, animation_rate: float = 0.01):
        super().__init__(input_data, animation_rate)
        self.group_by_row: dict[int, list[effect_char.EffectCharacter | None]] = {}

    def prepare_data(self) -> None:
        """Prepares the data for the effect by sorting by row and assigning the star symbol."""

        for character in self.characters:
            character.symbol = "*"
            character.graphical_effect.color = random.randint(1, 10)
            character.current_coord = effect_char.Coord(self.random_column(), self.output_area_top)
            self.pending_chars.append(character)
        for character in sorted(self.pending_chars, key=lambda c: c.input_coord.row):
            if character.input_coord.row not in self.group_by_row:
                self.group_by_row[character.input_coord.row] = []
            self.group_by_row[character.input_coord.row].append(character)

    def run(self) -> None:
        """Runs the effect."""
        self.prep_terminal()
        self.prepare_data()
        self.pending_chars.clear()
        while self.group_by_row or self.animating_chars or self.pending_chars:
            if not self.pending_chars and self.group_by_row:
                self.pending_chars.extend(self.group_by_row.pop(min(self.group_by_row.keys())))  # type: ignore
            if self.pending_chars:
                for _ in range(random.randint(1, 3)):
                    if self.pending_chars:
                        self.animating_chars.append(
                            self.pending_chars.pop(random.randint(0, len(self.pending_chars) - 1))
                        )
                    else:
                        break
            self.animate_chars()

            # tracking completed chars (remove if unnecessary)
            self.completed_chars.extend(
                [animating_char for animating_char in self.animating_chars if animating_char.animation_completed()]
            )
            self.maintain_completed()

            # remove completed chars from animating chars
            self.animating_chars = [
                animating_char for animating_char in self.animating_chars if not animating_char.animation_completed()
            ]

    def animate_chars(self) -> None:
        """Animates the characters by calling the tween method and printing the characters to the terminal."""
        for animating_char in self.animating_chars:
            tops.print_character(animating_char, clear_last=True)
            animating_char.move()
            if animating_char.animation_completed():
                animating_char.symbol = animating_char.input_symbol
                animating_char.graphical_effect = animating_char.final_graphical_effect

        time.sleep(self.animation_rate)
