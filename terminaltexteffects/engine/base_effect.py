"""Base classes for all effects.

Base classes from which all effects should inherit. These classes define the basic structure for an effect and
establish the effect iterator interface as well as the effect configuration and terminal configuration.

Classes:
    BaseEffectIterator(Generic[T]): An abstract base class that defines the basic structure for an iterator
        that applies a certain effect to the input data. Provides initilization for the effect configuration and
        terminal as well as the `__iter__` method.

    BaseEffect(Generic[T]): An abstract base class that defines the basic structure for an effect. Provides
        the `__iter__` method and a context manager for terminal output.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from copy import deepcopy
from typing import TYPE_CHECKING, Generic, TypeVar
from enum import Enum, auto
from terminaltexteffects.engine.animation import Scene
from terminaltexteffects.engine.motion import Coord
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
import time

from terminaltexteffects.utils import easing

if TYPE_CHECKING:
    from collections.abc import Generator

    from terminaltexteffects.engine.base_character import EffectCharacter

T = TypeVar("T", bound=BaseConfig)


class ParticleEmitter:
    class Emittertype(Enum):
        RADIAL = auto()

    def __init__(self, symbol: str, coord: Coord, rate: float, terminal: Terminal) -> None:
        self.symbol = symbol
        self.current_coord = coord
        self.rate = rate
        self.time_between_emissions = 1 / rate
        self.terminal = terminal
        self.available_particles: set[EffectCharacter] = set()
        self.active_particles: set[EffectCharacter] = set()
        self.last_emission_time = time.monotonic()
        self.host_character: EffectCharacter | None = None
        for _ in range(30):
            particle = self.terminal.add_character(symbol=symbol, coord=self.current_coord)
            self.available_particles.add(particle)

    def _reset_particle(self, particle: EffectCharacter) -> None:
        self.active_particles.remove(particle)
        self.available_particles.add(particle)
        particle.motion.paths.clear()
        particle.motion.set_coordinate(self.current_coord)
        if particle.animation.active_scene:
            particle.animation.active_scene.reset_scene()
        particle.event_handler.registered_events.clear()
        self.terminal.set_character_visibility(particle, is_visible=False)

    def set_scene(self, scene: Scene) -> None:
        for particle in self.available_particles:
            particle.animation.scenes[scene.scene_id] = deepcopy(scene)
            particle.animation.activate_scene(scene.scene_id)

    def emit(self) -> EffectCharacter | None:
        if (self.terminal.now - self.last_emission_time) < self.time_between_emissions:
            return None
        if self.host_character:
            self.current_coord = self.host_character.motion.current_coord
        self.last_emission_time = self.terminal.now
        if not self.available_particles:
            return None
        next_particle = self.available_particles.pop()
        next_particle.motion.set_coordinate(self.current_coord)
        self.active_particles.add(next_particle)
        path = next_particle.motion.new_path(speed=0.1)
        next_coord = Coord(column=self.current_coord.column, row=self.terminal.canvas.top)
        path.new_waypoint(coord=next_coord)

        next_particle.event_handler.register_event(
            event=next_particle.event_handler.Event.PATH_COMPLETE,
            caller=path,
            action=next_particle.event_handler.Action.CALLBACK,
            target=next_particle.event_handler.Callback(self._reset_particle),
        )

        next_particle.motion.activate_path(path)
        next_particle.animation.activate_scene("particle")
        self.terminal.set_character_visibility(next_particle, is_visible=True)
        return next_particle


class BaseEffectIterator(ABC, Generic[T]):
    """Base iterator class for all effects.

    Args:
        effect (BaseEffect): Effect to apply to the input data.

    Attributes:
        config (T): Configuration for the effect.
        terminal (Terminal): Terminal to use for output.
        active_characters (set[EffectCharacter]): Set of active characters in the effect.
        preexisting_colors_present (bool): Whether any characters in the input data have preexisting colors.
    Properties:
        frame (str): Current frame of the effect.

    Methods:
        update: Run the tick method for all active characters and remove inactive characters from the active list.
        __iter__: Return the iterator object.
        __next__: Return the next frame of the effect.

    """

    def __init__(self, effect: BaseEffect) -> None:
        """Initialize the iterator with the Effect.

        Args:
            effect (BaseEffect): Effect to apply to the input data.

        """
        self.config: T = deepcopy(effect.effect_config)
        self.terminal = Terminal(effect.input_data, deepcopy(effect.terminal_config))
        self.active_characters: set[EffectCharacter] = set()
        self.preexisting_colors_present: bool = any(
            any((character.animation.input_fg_color, character.animation.input_bg_color))
            for character in self.terminal.get_characters()
        )
        self.emitters: list[ParticleEmitter] = []

    @property
    def frame(self) -> str:
        """Return the current frame by getting the formatted output string from the terminal.

        If the frame rate is set >0 in the terminal configuration, enforce the frame rate.

        Returns:
            str: Current frame of the effect.

        """
        if self.terminal._frame_rate:
            self.terminal.enforce_framerate()
        return self.terminal.get_formatted_output_string()

    def get_emitter(self, symbol: str, coord: Coord, rate: float) -> ParticleEmitter:
        emitter = ParticleEmitter(symbol, coord, rate, self.terminal)
        emitter.emit()
        self.emitters.append(emitter)
        return emitter

    def update(self) -> None:
        """Run the tick method for all active characters.

        Remove inactive characters from the active_characters set.
        """
        self.terminal.now = time.monotonic()
        for emitter in self.emitters:
            particle = emitter.emit()
            if particle is not None:
                self.active_characters.add(particle)

        for character in self.active_characters:
            character.tick()
        self.active_characters -= {character for character in self.active_characters if not character.is_active}

    def __iter__(self) -> BaseEffectIterator:
        """Return the iterator object.

        Returns:
            BaseEffectIterator: Iterator object.

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

    def __iter__(self) -> BaseEffectIterator:
        """Return the iterator object.

        Returns:
            BaseEffectIterator: Iterator object.

        """
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

        finally:
            terminal.restore_cursor(end_symbol)
