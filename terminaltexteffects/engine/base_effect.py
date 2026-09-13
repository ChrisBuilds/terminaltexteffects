"""Base classes for all effects.

Base classes from which all effects should inherit. These classes define the basic structure for an effect and
establish the effect iterator interface as well as the effect configuration and terminal configuration.

Classes:
    BaseEffectIterator(Generic[T]): An abstract base class that defines the basic structure for an iterator
        that applies a certain effect to the input data. Provides initialization for the effect configuration and
        terminal as well as the `__iter__` method.

    BaseEffect(Generic[T]): An abstract base class that defines the basic structure for an effect. Provides
        the `__iter__` method and a context manager for terminal output.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar
from weakref import ReferenceType, ref

from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.utils.exceptions import EmptyInputError

if TYPE_CHECKING:
    from collections.abc import Generator

    from terminaltexteffects.engine.base_character import EffectCharacter

T = TypeVar("T", bound=BaseConfig)


@dataclass
class _TerminalOutputContext:
    """Track a terminal staged for one active output context.

    The first iterator created inside the context consumes `terminal`. Further
    iterators remain fresh and build their own terminal graphs.
    """

    terminal: Terminal
    available_to_iterator: bool


class BaseEffectIterator(ABC, Generic[T]):
    """Base iterator class for all effects.

    Args:
        effect (BaseEffect): Effect to apply to the input data.

    Attributes:
        config (T): Configuration for the effect.
        terminal (Terminal): Terminal to use for output.
        active_characters (set[EffectCharacter]): Set of active characters in the effect.
        preexisting_colors_present (bool): Whether any terminal input characters were
            initialized with parsed foreground or background input colors.
    Properties:
        frame (str): Current frame of the effect.

    Methods:
        update: Run the tick method for all active characters and remove inactive characters from the active list.
        __iter__: Return the iterator object.
        __next__: Return the next frame of the effect.

    Raises:
        EmptyInputError: The configured canvas contains no visible input characters.

    """

    def __init__(self, effect: BaseEffect) -> None:
        """Initialize the iterator with the Effect.

        Args:
            effect (BaseEffect): Effect to apply to the input data.

        """
        self.config: T = deepcopy(effect.effect_config)
        self.terminal = effect._acquire_terminal()
        if not self.terminal.get_characters():
            raise EmptyInputError
        self.active_characters: set[EffectCharacter] = set()
        self.preexisting_colors_present: bool = any(
            any((character.animation.input_fg_color, character.animation.input_bg_color))
            for character in self.terminal.get_characters()
        )

    @property
    def frame(self) -> str:
        """Return the current formatted frame from the terminal.

        If the configured terminal frame rate is greater than `0`, enforce the frame rate
        before reading the formatted output string. This property does not advance effect
        state on its own.

        Returns:
            str: Current frame of the effect.

        """
        if self.terminal._frame_rate:
            self.terminal.enforce_framerate()
        return self.terminal.get_formatted_output_string()

    def update(self) -> None:
        """Run one tick for each active character and prune inactive characters.

        Each character in `active_characters` is ticked once. After all ticks complete,
        characters whose `is_active` flag is false are removed from the set.
        """
        for character in tuple(self.active_characters):
            character.tick()
        self.active_characters -= {character for character in self.active_characters if not character.is_active}

    def __iter__(self) -> BaseEffectIterator:
        """Return this iterator instance.

        Returns:
            BaseEffectIterator: This iterator.

        """
        return self

    @abstractmethod
    def __next__(self) -> str:
        """Return the next frame of the effect.

        Perform any necessary updates to the effect to progress
        the effect logic and return the next frame.

        Raises:
            NotImplementedError: This method must be implemented by the subclass.

        Returns:
            str: Next frame of the effect.

        """


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

    @property
    @abstractmethod
    def _iterator_cls(self) -> type[BaseEffectIterator]:
        """Effect iterator class as a subclass of BaseEffectIterator."""

    def __init__(
        self,
        input_data: str,
        effect_config: T | None = None,
        terminal_config: TerminalConfig | None = None,
    ) -> None:
        """Initialize the effect with the input data.

        Args:
            input_data (str): Text to which the effect will be applied.
            effect_config (BaseConfig | None, optional): Effect configuration. If not
                provided, a new configuration will be built with default values.
                Defaults to None.
            terminal_config (TerminalConfig | None, optional): Terminal configuration. If not
                provided, a new configuration will be built with default values.
                Defaults to None.

        """
        self.input_data = input_data
        self.effect_config: T = effect_config or self._config_cls._build_config()
        self.terminal_config: TerminalConfig = terminal_config or TerminalConfig._build_config()
        self._terminal_output_contexts: list[_TerminalOutputContext] = []
        self._pending_terminal_ref: ReferenceType[Terminal] | None = None

    def _build_terminal(self) -> Terminal:
        """Build a fresh terminal from the effect's current input and configuration."""
        return Terminal(self.input_data, deepcopy(self.terminal_config))

    def _acquire_terminal(self) -> Terminal:
        """Return a staged output terminal when available, otherwise build a fresh one.

        A newly built terminal is retained weakly so a following `terminal_output()`
        context can use the same graph without extending the iterator's lifetime.
        """
        if self._terminal_output_contexts:
            output_context = self._terminal_output_contexts[-1]
            if output_context.available_to_iterator:
                output_context.available_to_iterator = False
                return output_context.terminal
        terminal = self._build_terminal()
        self._pending_terminal_ref = ref(terminal)
        return terminal

    def __iter__(self) -> BaseEffectIterator:
        """Create and return a new iterator for the effect.

        Returns:
            BaseEffectIterator: A new iterator instance for this effect.

        """
        return self._iterator_cls(self)

    @contextmanager
    def terminal_output(self, end_symbol: str = "\n") -> Generator[Terminal, None, None]:
        """Prepare a shared iterator terminal for output and restore it afterward.

        When called before iteration, the context stages its terminal for the first
        iterator created inside it. When an iterator was created immediately before
        the context, that iterator's terminal is reused instead. Every call to
        `iter(effect)` still creates a fresh iterator, and only one iterator consumes
        each context-staged terminal.

        Args:
            end_symbol (str, optional): Symbol to print after the effect has completed. Defaults to newline.

        Yields:
            Terminal: Terminal object for handling output.

        Raises:
            Exception: Any exception that occurs within the context manager is re-raised
                after the terminal state is restored.

        """
        pending_terminal = self._pending_terminal_ref() if self._pending_terminal_ref is not None else None
        if pending_terminal is None:
            terminal = self._build_terminal()
            output_context = _TerminalOutputContext(terminal, available_to_iterator=True)
        else:
            terminal = pending_terminal
            output_context = _TerminalOutputContext(terminal, available_to_iterator=False)
        self._pending_terminal_ref = None
        self._terminal_output_contexts.append(output_context)
        try:
            terminal.prep_canvas()
            yield terminal

        finally:
            self._terminal_output_contexts.pop()
            terminal.restore_cursor(end_symbol)
