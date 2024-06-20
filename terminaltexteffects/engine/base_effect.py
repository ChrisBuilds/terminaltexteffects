"""This module contains base classes for all effects.

Base classes from which all effects should inherit. These classes define the basic structure for an effect and establish the
effect iterator interface as well as the effect configuration and terminal configuration.

Classes:
    BaseEffectIterator(Generic[T]): An abstract base class that defines the basic structure for an iterator
        that applies a certain effect to the input data. Provides initilization for the effect configuration and terminal
        as well as the `__iter__` method.

    BaseEffect(Generic[T]): An abstract base class that defines the basic structure for an effect. Provides the `__iter__`
        method and a context manager for terminal output.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from copy import deepcopy
from typing import Generator, Generic, TypeVar

from terminaltexteffects.engine.base_character import EffectCharacter
from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.utils.argsdataclass import ArgsDataClass

T = TypeVar("T", bound=ArgsDataClass)


class BaseEffectIterator(ABC, Generic[T]):
    """Base iterator class for all effects.

    Args:
        effect (BaseEffect): Effect to apply to the input data.

    Attributes:
        config (T): Configuration for the effect.
        terminal (Terminal): Terminal to use for output.
        active_characters (list[EffectCharacter]): List of active characters in the effect.

    Properties:
        frame (str): Current frame of the effect.

    Methods:
        update: Run the tick method for all active characters and remove inactive characters from the active list.
        __iter__: Return the iterator object.
        __next__: Return the next frame of the effect.
    """

    def __init__(self, effect: "BaseEffect") -> None:
        """Initialize the iterator with the Effect.

        Args:
            effect (BaseEffect): Effect to apply to the input data.
        """
        self.config: T = deepcopy(effect.effect_config)
        self.terminal = Terminal(effect.input_data, deepcopy(effect.terminal_config))
        self.active_characters: list[EffectCharacter] = []

    @property
    def frame(self) -> str:
        """Return the current frame by getting the formatted output string from the terminal. If the frame rate is set >0
        in the terminal configuration, enforce the frame rate.

        Returns:
            str: Current frame of the effect.
        """
        if self.terminal._frame_rate:
            self.terminal.enforce_framerate()
        return self.terminal.get_formatted_output_string()

    def update(self) -> None:
        """Run the tick method for all active characters and remove inactive characters from the active list."""
        for character in self.active_characters:
            character.tick()
        self.active_characters = [character for character in self.active_characters if character.is_active]

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
    def terminal_output(self, end_symbol: str = "\n") -> Generator[Terminal, None, None]:
        """Context manager for terminal output. Prepares the terminal for output and restores it after.

        Args:
            end_symbol (str, optional): Symbol to print after the effect has completed. Defaults to newline.

        Yields:
            Terminal: Terminal object for handling output.

        Raises:
            Exception: Any exception that occurs within the context manager will be raised before restoring the terminal
                state.
        """
        terminal = Terminal(self.input_data, self.terminal_config)
        try:
            terminal.prep_canvas()
            yield terminal
        except:  # noqa: E722
            raise
        finally:
            terminal.restore_cursor(end_symbol)
