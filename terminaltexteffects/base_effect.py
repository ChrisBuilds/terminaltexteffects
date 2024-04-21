from abc import ABC, abstractmethod
from contextlib import contextmanager
from copy import deepcopy
from typing import Generic, TypeVar

from terminaltexteffects.utils.argsdataclass import ArgsDataClass
from terminaltexteffects.utils.terminal import Terminal, TerminalConfig

T = TypeVar("T", bound=ArgsDataClass)


class BaseEffectIterator(ABC, Generic[T]):
    """Base iterator class for all effects.

    Args:
        effect (BaseEffect): Effect to apply to the input data.

    Attributes:
        _config (T): Configuration for the effect.
        _terminal (Terminal): Terminal to use for output.
    """

    def __init__(self, effect: "BaseEffect") -> None:
        self._config: T = deepcopy(effect.effect_config)
        self._terminal = Terminal(effect.input_data, deepcopy(effect.terminal_config))

    def __iter__(self) -> "BaseEffectIterator":
        return self

    @abstractmethod
    def __next__(self) -> str:
        raise NotImplementedError


class BaseEffect(ABC, Generic[T]):
    """Base iterable class for all effects."""

    @property
    @abstractmethod
    def _config_cls(self) -> type[T]:
        """Effect configuration class as a subclass of ArgsDataClass."""
        raise NotImplementedError

    @property
    @abstractmethod
    def _iterator_cls(self) -> type[BaseEffectIterator]:
        """Effect iterator class as a subclass of BaseEffectIterator."""
        raise NotImplementedError

    def __init__(self, input_data: str) -> None:
        """Initialize the effect with the input data.

        Args:
            input_data (str): Data to apply the effect to.
            terminal_config (TerminalConfig | None): Configuration for the terminal.
        """
        self.input_data = input_data
        self.effect_config = self._config_cls()
        self.terminal_config = TerminalConfig()

    def __iter__(self) -> BaseEffectIterator:
        return self._iterator_cls(self)

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
