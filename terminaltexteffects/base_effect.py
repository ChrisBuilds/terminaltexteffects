"""This module contains base classes for all effects.

Base classes from which all effects should inherit. These classes define the basic structure for an effect and establish the
effect iterator interface as well as the effect configuration and terminal configuration.

Classes:
    BaseEffectIterator(Generic[T]): An abstract base class that defines the basic structure for an iterator
        that applies a certain effect to the input data. Provides initilization for the effect configuration and terminal
        as well as the `__iter__` method.

    BaseEffect(Generic[T]): An abstract base class that defines the basic structure for an effect. Provides the `__iter__`
        method and a context manager for terminal output.

Usage Example:

    class MyEffectIterator(BaseEffectIterator[MyEffectConfig]):
        def __init__(self, effect: "MyEffect") -> None:
            super().__init__(effect)
            # Custom initialization code here

        def __next__(self) -> str:
            # Custom iteration code here
            return next_frame

    class MyEffect(BaseEffect[MyEffectConfig]):
        _config_cls = MyEffectConfig
        _iterator_cls = MyEffectIterator

        def __init__(self, input_data: str) -> None:
            super().__init__(input_data)

"""

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
        """Initialize the iterator with the Effect.

        Args:
            effect (BaseEffect): Effect to apply to the input data.
        """
        self._config: T = deepcopy(effect.effect_config)
        self._terminal = Terminal(effect.input_data, deepcopy(effect.terminal_config))

    def __iter__(self) -> "BaseEffectIterator":
        return self

    @abstractmethod
    def __next__(self) -> str:
        raise NotImplementedError


class BaseEffect(ABC, Generic[T]):
    """Base iterable class for all effects.

    Base class for all effects. Provides the `__iter__` method and a context manager for terminal output.

    Attributes:
        input_data (str): Text to which the effect will be applied.
        effect_config (T): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.
    """

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
            input_data (str): Text to which the effect will be applied.
        """
        self.input_data = input_data
        self.effect_config = self._config_cls()
        self.terminal_config = TerminalConfig()

    def __iter__(self) -> BaseEffectIterator:
        return self._iterator_cls(self)

    @contextmanager
    def terminal_output(self):
        """Context manager for terminal output. Prepares the terminal for output and restores it after.

        Yields:
            terminal (Terminal): Terminal object for output.

        Raises:
            Exception: Any exception that occurs within the context manager.
        """
        terminal = Terminal(self.input_data, self.terminal_config)
        try:
            terminal.prep_outputarea()
            yield terminal
        except:  # noqa: E722
            raise
        finally:
            terminal.restore_cursor()
