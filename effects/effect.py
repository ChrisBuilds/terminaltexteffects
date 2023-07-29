import utils.terminaloperations as tops
from utils import utils
from effects.effect_char import EffectCharacter


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
        self.characters = [
            character for character in self.characters if character.final_coord.row < self.terminal_height - 1
        ]
        self.input_height = len(input_data.splitlines())
        self.input_width = max([character.final_coord.column for character in self.characters])
        self.output_area_top = min(self.terminal_height - 1, self.input_height)
        "Distance to the top row of the adjusted output area. Top of the terminal if input is too long."
        self.pending_chars: list[EffectCharacter] = []
        self.animating_chars: list[EffectCharacter] = []
        self.completed_chars: list[EffectCharacter] = []

    def prep_terminal(self) -> None:
        """Prepares the terminal for the effect by adding empty lines above."""
        print("\n" * self.input_height)

    def maintain_completed(self) -> None:
        """Print completed characters in case they've been overwritten."""
        for completed_char in self.completed_chars:
            tops.print_character(completed_char)
