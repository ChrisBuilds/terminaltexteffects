from abc import ABC, abstractmethod
from contextlib import contextmanager

from terminaltexteffects.utils.terminal import Terminal, TerminalConfig


class BaseEffectIterator(ABC):
    """Base iterator class for all effects."""

    def __init__(self, input_data: str, terminal_config: TerminalConfig):
        self._terminal = Terminal(input_data, terminal_config)

    def __iter__(self) -> "BaseEffectIterator":
        return self

    @abstractmethod
    def __next__(self) -> str:
        raise NotImplementedError


class BaseEffect(ABC):
    """Base iterable class for all effects."""

    def __init__(self, input_data: str, terminal_config: TerminalConfig | None = None):
        """Initialize the effect with the input data.

        Args:
            input_data (str): Data to apply the effect to.
            terminal_config (TerminalConfig | None): Configuration for the terminal.
        """
        self.input_data = input_data
        if terminal_config is None:
            self.terminal_config = TerminalConfig()
        else:
            self.terminal_config = terminal_config

    @abstractmethod
    def __iter__(self) -> BaseEffectIterator:
        raise NotImplementedError

    @contextmanager
    def terminal_output(self):
        """Context manager for terminal output. Prepares the terminal for output and restores it after."""
        terminal = Terminal(self.input_data, self.terminal_config)
        try:
            terminal.prep_outputarea()
            yield terminal
        except:  # noqa: E722
            raise
        finally:
            terminal.restore_cursor()
