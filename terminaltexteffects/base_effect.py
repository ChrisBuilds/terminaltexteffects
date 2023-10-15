import random, argparse
import terminaltexteffects.utils.terminal as terminal
from terminaltexteffects.base_character import EffectCharacter


class Effect:
    """Generic class for all effects. Derive from this class to create a new effect.

    The Effect object contains a reference to the Terminal object, arguments, and lists of pending and animating characters.
    The Effect object is used to manage the state of the effect and the characters that are part of the effect.
    There are methods for retrieving characters by row and column, and for getting random row and column positions within the output area.

    Attributes:
        terminal (terminal.Terminal): a Terminal object.
        args (argparse.Namespace): arguments passed to the program.
        pending_chars (list[EffectCharacter]): a list of pending EffectCharacters.
        animating_chars (list[EffectCharacter]): a list of animating EffectCharacters.
    """

    def __init__(self, terminal: terminal.Terminal, args: argparse.Namespace):
        """Initializes the Effect class.

        Args:
            terminal (terminal.Terminal): a Terminal object.
        """
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.animating_chars: list[EffectCharacter] = []
