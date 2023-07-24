import utils.terminaloperations as tops
from utils import utils


class Effect:
    """Generic class for all effects. Derive from this class to create a new effect."""

    def __init__(self, input_data: str):
        """Initializes the Effect class.

        Args:
            input_data (str): string from stdin
        """
        self.input_data = input_data
        self.terminal_width, self.terminal_height = tops.get_terminal_dimensions()
        self.characters = utils.decompose_input(input_data)
        self.characters = [character for character in self.characters if character.y < self.terminal_height - 1]
        self.input_height = len(input_data.splitlines())
        self.input_width = max([character.x for character in self.characters])
        self.pending_chars: list[EffectCharacter] = []
        self.animating_chars: list[EffectCharacter] = []
        self.completed_chars: list[EffectCharacter] = []

    def prep_terminal(self) -> None:
        """Prepares the terminal for the effect by adding empty lines above."""
        print("\n" * self.input_height)

    def maintain_completed(self) -> None:
        """Print completed characters in case they've been overwritten."""
        for completed_char in self.completed_chars:
            tops.print_character_at_relative_position(
                completed_char.character, completed_char.target_x, completed_char.target_y
            )


class EffectCharacter:
    def __init__(self, character: utils.Character, current_x: int, current_y: int):
        """Base class for effect characters.

        Args:
            character (utils.Character): utils.Character object
            current_x (int): Initialize with starting x position
            current_y (int): Initialize with starting y position
        """
        self.character: str = character.symbol
        self.target_x: int = character.x
        self.target_y: int = character.y
        self.current_x: int = current_x
        self.current_y: int = current_y
        self.last_x: int | None = None
        self.last_y: int | None = None
        self.tween_delta = 0
        self.tweened_x = 0
        self.tweened_y = 0

    def tween(self) -> None:
        """Moves the character one step closer to the target position."""
        self.last_x = self.current_x
        self.last_y = self.current_y
        x_distance = abs(self.current_x - self.target_x)
        y_distance = abs(self.current_y - self.target_y)
        # on first call, calculate the x and y movement distance to approximate an angled line
        if not self.tween_delta:
            self.tweened_x = self.current_x
            self.tweened_y = self.current_y
            self.tween_delta = min(x_distance, y_distance) / max(x_distance, y_distance, 1)
            if self.tween_delta == 0:
                self.tween_delta = 1

            if x_distance < y_distance:
                self.x_delta = self.tween_delta
                self.y_delta = 1
            elif y_distance < x_distance:
                self.y_delta = self.tween_delta
                self.x_delta = 1
            else:
                self.x_delta = self.y_delta = 1
        # adjust the x and y positions by the calculated delta, round down to int
        if self.current_x < self.target_x:
            self.tweened_x += self.x_delta
            self.current_x = int(self.tweened_x)
        elif self.current_x > self.target_x:
            self.tweened_x -= self.x_delta
            self.current_x = int(self.tweened_x)
        if self.current_y < self.target_y:
            self.tweened_y += self.y_delta
            self.current_y = int(self.tweened_y)
        elif self.current_y > self.target_y:
            self.tweened_y -= self.y_delta
            self.current_y = int(self.tweened_y)
