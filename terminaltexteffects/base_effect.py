from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any

from terminaltexteffects.utils.terminal import Terminal, TerminalConfig


class BaseEffect(ABC):
    """Base class for all effects."""

    @abstractmethod
    def __init__(self, input_data: str, effect_config: Any, terminal_config: TerminalConfig):
        """Initialize the effect with the input data.

        Args:
            input_data (str): Data to apply the effect to.
            effect_config (ArgsDataClass): Configuration for the effect.
            terminal_config (TerminalConfig): Configuration for the terminal.
        """
        self.input_data = input_data
        self.config = effect_config
        self.terminal = Terminal(input_data, terminal_config)

    @abstractmethod
    def build(self) -> None:
        """(re)Build the effect."""
        pass

    @property
    @abstractmethod
    def built(self) -> bool:
        """Returns True if the effect has been built."""
        pass

    @abstractmethod
    def __iter__(self) -> Iterator[str]:
        """Runs the effect and yields the output frames as strings."""
        pass
