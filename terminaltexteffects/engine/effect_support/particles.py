"""Reusable particle helpers for effect-owned helper characters.

The particle API wraps a group of `EffectCharacter` instances created with
`Terminal.add_character()` and lets an effect reuse them as short-lived visual
elements such as smoke, sparks, fragments, or other transient decorations.
Particles are still normal characters: effects configure their animation
scenes, motion paths, event callbacks, layer, and appearance with the regular
`EffectCharacter` APIs.

`ParticlePool` intentionally manages only the pooling lifecycle. It tracks
which helper characters are available, creates new ones when permitted, moves
emitted particles to the requested origin, adds visible particles to the
iterator's `active_characters` set, and returns released particles to the
available collection. Effects retain ownership of particle behavior by passing
configuration callbacks to `emit()` and by choosing which state should be
cleared through `ParticleReset`.
"""

from __future__ import annotations

import random
import typing
from collections import deque
from dataclasses import dataclass

from terminaltexteffects.engine.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils.geometry import Coord

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Iterable, MutableSet, Sequence

    from terminaltexteffects.engine.animation import Scene
    from terminaltexteffects.engine.motion import Path
    from terminaltexteffects.engine.terminal import Terminal


@dataclass(frozen=True)
class ParticleReset:
    """Select mutable particle state to clear before reuse.

    A particle can carry paths, scenes, event registrations, active motion,
    active animation, and its last rendered appearance from a previous emission.
    `ParticleReset` lets callers choose which of that state is discarded when
    a particle is acquired from a pool.

    The default reset is conservative for common particle effects: it
    deactivates any active path or scene and clears old paths, while preserving
    scenes and event registrations. This supports the typical pattern of
    creating reusable particle scenes and recycling callbacks once in an
    initializer, then building short-lived paths for each emission.

    Attributes:
        clear_paths: Remove all stored motion paths from the particle. Enable
            this when paths are generated per emission.
        clear_scenes: Remove all stored animation scenes from the particle.
            Leave this disabled when scenes are prebuilt once and reused.
        clear_events: Remove all registered event actions from the particle.
            Leave this disabled when lifecycle callbacks, such as reclaim-on-
            event registrations, should survive across emissions.
        deactivate_path: Deactivate the currently active path, if any, before
            the particle is configured again.
        deactivate_scene: Deactivate the currently active scene, if any, before
            the particle is configured again.
        reset_appearance: Restore the particle's current visual to its
            `input_symbol`. This is useful when previous emissions changed
            the symbol or colors outside a reusable scene.

    """

    clear_paths: bool = True
    clear_scenes: bool = False
    clear_events: bool = False
    deactivate_path: bool = True
    deactivate_scene: bool = True
    reset_appearance: bool = False


DEFAULT_PARTICLE_RESET = ParticleReset()


class ParticlePool:
    """Manage a pool of reusable helper characters for effects.

    A pool owns a set of added `EffectCharacter` objects and divides them into
    two practical states:

    - available particles, which may be acquired or emitted again
    - active particles, which have been emitted and added to the effect
      iterator's `active_characters` set

    Particles are created with one of the configured symbols at the pool's
    default coordinate. They are hidden by the terminal until emitted. `emit()`
    positions an acquired particle, calls an effect-provided configuration
    callback, sets visibility, and marks it active. `reclaim()` reverses that
    lifecycle by optionally hiding and deactivating the character, removing it
    from `active_characters`, and returning it to the available queue.

    The pool does not define particle visuals or motion. Effects should use the
    `initializer` callback for one-time setup, such as reusable scenes,
    persistent event callbacks, or layer assignment, and use the `on_emit`
    callback passed to `emit()` for per-emission setup, such as coordinates,
    paths, scene resets, random targets, or scene activation.

    Args:
        terminal: Terminal used to create helper characters and control their
            visibility.
        active_characters: The owning effect iterator's active character set.
            Emitted particles are added to this set and released particles are
            removed from it.
        symbols: One symbol or a sequence of symbols to use when creating
            particles. When a sequence is provided, new particles choose a
            symbol randomly unless `acquire()` or `emit()` overrides it.
        initial_count: Number of helper characters to create immediately.
        max_size: Maximum number of particles the pool may own. `None` allows
            unbounded lazy growth as particles are acquired.
        coord: Initial coordinate for newly created particles. Defaults to
            `Coord(0, 0)`.
        initializer: Optional callback invoked once for each newly created
            particle. It is the right place for setup that should survive reuse.

    Raises:
        ValueError: If `symbols` is empty, `initial_count` is negative, or
            `max_size` is smaller than `initial_count`.

    Attributes:
        terminal: Terminal that owns the added particle characters.
        active_characters: Active character set supplied by the owning iterator.
        symbols: Tuple of candidate symbols for lazily created particles.
        max_size: Optional cap on the number of owned particles.
        coord: Default creation coordinate for new particles.
        initializer: Optional one-time setup callback for new particles.
        available: Queue of particles ready to be reused.
        particles: All particles owned by the pool, both active and available.

    """

    def __init__(
        self,
        terminal: Terminal,
        active_characters: MutableSet[EffectCharacter],
        symbols: Sequence[str] | str,
        *,
        initial_count: int = 0,
        max_size: int | None = None,
        coord: Coord | None = None,
        initializer: Callable[[EffectCharacter], None] | None = None,
    ) -> None:
        """Initialize a particle pool and optionally preallocate particles.

        Args:
            terminal: Terminal used to create helper characters and control
                their visibility.
            active_characters: The effect iterator's active character set.
            symbols: Symbol or symbols used when creating new particles.
            initial_count: Number of particles to create immediately and place
                in the available queue.
            max_size: Maximum number of particles the pool may own. `None`
                allows lazy growth whenever the available queue is empty.
            coord: Initial coordinate for newly created particles. Defaults to `Coord(0, 0)`.
            initializer: Optional callback run once for each newly created
                particle. Use it for persistent setup such as reusable scenes,
                reclaim callbacks, or layer assignment.

        Raises:
            ValueError: If the pool cannot be constructed with the requested
                symbol set or size constraints.

        """
        if isinstance(symbols, str):
            symbols = (symbols,)
        if not symbols:
            message = "ParticlePool requires at least one symbol."
            raise ValueError(message)
        if initial_count < 0:
            message = "initial_count must be non-negative."
            raise ValueError(message)
        if max_size is not None and max_size < initial_count:
            message = "max_size must be greater than or equal to initial_count."
            raise ValueError(message)

        self.terminal = terminal
        self.active_characters = active_characters
        self.symbols = tuple(symbols)
        self.max_size = max_size
        self.coord = coord or Coord(0, 0)
        self.initializer = initializer
        self.available: deque[EffectCharacter] = deque()
        self.particles: list[EffectCharacter] = []

        for _ in range(initial_count):
            self.available.append(self._create_particle())

    def __len__(self) -> int:
        """Return the number of particles owned by the pool.

        This includes particles currently available for reuse and particles
        currently active in the effect.

        """
        return len(self.particles)

    def _create_particle(self, symbol: str | None = None) -> EffectCharacter:
        """Create a hidden helper character and add it to the pool.

        Args:
            symbol: Optional symbol for the new particle. When omitted, one of
                the pool's configured symbols is selected randomly.

        Returns:
            The newly created `EffectCharacter` after the optional initializer
            has run.

        """
        particle = self.terminal.add_character(symbol or random.choice(self.symbols), self.coord)
        if self.initializer is not None:
            self.initializer(particle)
        self.particles.append(particle)
        return particle

    @staticmethod
    def _reset_particle(character: EffectCharacter, reset: ParticleReset) -> None:
        """Apply a reset policy to a particle before it is reused.

        Args:
            character: Particle character to reset.
            reset: Reset policy controlling which mutable subsystems are
                deactivated or cleared.

        """
        if reset.deactivate_path:
            character.motion.deactivate_path()
        if reset.deactivate_scene:
            character.animation.deactivate_scene()
        if reset.clear_paths:
            character.motion.paths.clear()
        if reset.clear_scenes:
            character.animation.scenes.clear()
        if reset.clear_events:
            character.event_handler.registered_events.clear()
        if reset.reset_appearance:
            character.animation.set_appearance(character.input_symbol)

    def acquire(
        self,
        *,
        symbol: str | None = None,
        reset: ParticleReset = DEFAULT_PARTICLE_RESET,
    ) -> EffectCharacter | None:
        """Check out a particle for manual configuration.

        `acquire()` returns an available particle when possible. If the
        available queue is empty and the pool has not reached `max_size`, a new
        particle is created lazily. If the pool is capped and all particles are
        checked out, `None` is returned.

        The selected `ParticleReset` is applied before the particle is
        returned. Passing `symbol` updates the particle's `input_symbol` and
        current appearance so the new symbol is used for subsequent resets and
        rendering.

        Args:
            symbol: Optional symbol override for the acquired particle.
            reset: State reset policy to apply before returning the particle.

        Returns:
            An `EffectCharacter` ready to configure, or `None` when a capped
            pool has no available capacity.

        """
        if self.available:
            particle = self.available.pop()
            self._reset_particle(particle, reset)
            if symbol is not None:
                particle._input_symbol = symbol
                particle.animation.set_appearance(symbol)
            return particle

        if self.max_size is not None and len(self.particles) >= self.max_size:
            return None

        particle = self._create_particle(symbol)
        self._reset_particle(particle, reset)
        return particle

    def emit(
        self,
        origin: Coord,
        on_emit: Callable[[EffectCharacter], None],
        *,
        symbol: str | None = None,
        visible: bool = True,
        reset: ParticleReset = DEFAULT_PARTICLE_RESET,
    ) -> EffectCharacter | None:
        """Acquire, position, prepare, show, and activate a particle.

        This is the high-level particle lifecycle helper most effects should
        use. It checks out a particle with `acquire()`, moves it to `origin`,
        calls `on_emit` so the effect can create or activate paths and
        scenes, sets terminal visibility, and adds the particle to
        `active_characters` so the iterator updates it on subsequent frames.

        If the pool is exhausted, `on_emit` is not called and `None` is
        returned.

        Args:
            origin: Coordinate where the particle should start this emission.
            on_emit: Callback that receives the acquired particle and applies
                per-emission behavior, such as paths, scene resets, random
                targets, or active scene/path selection.
            symbol: Optional symbol override passed through to `acquire()`.
            visible: Whether the terminal should render the particle
                immediately after configuration.
            reset: State reset policy passed through to `acquire()`.

        Returns:
            The emitted particle, or `None` when a capped pool is exhausted.

        """
        particle = self.acquire(symbol=symbol, reset=reset)
        if particle is None:
            return None

        particle.motion.set_coordinate(origin)
        on_emit(particle)
        self.terminal.set_character_visibility(particle, is_visible=visible)
        self.active_characters.add(particle)
        return particle

    def reclaim(
        self,
        character: EffectCharacter,
        *,
        hide: bool = True,
        deactivate: bool = True,
    ) -> None:
        """Reclaim a particle into the available queue.

        `reclaim()` removes the particle from the effect iterator's active
        set, optionally hides it, optionally deactivates its current path and
        scene, and makes it eligible for future `acquire()` or `emit()`
        calls. Stored paths, scenes, and event registrations are not cleared by
        reclaiming; use `ParticleReset` on the next acquire to clear that state.

        Calling `reclaim()` more than once for the same particle will not add
        duplicate entries to the available queue.

        Args:
            character: Particle character to return to the pool.
            hide: Hide the character in the terminal before making it available.
            deactivate: Deactivate any active path and scene before making the
                character available.

        """
        if hide:
            self.terminal.set_character_visibility(character, is_visible=False)
        if deactivate:
            character.motion.deactivate_path()
            character.animation.deactivate_scene()
        self.active_characters.discard(character)
        if character not in self.available:
            self.available.append(character)

    def reclaim_on_event(
        self,
        character: EffectCharacter,
        caller: Scene | Path | str,
        *,
        event: EventHandler.Event = EventHandler.Event.SCENE_COMPLETE,
        hide: bool = True,
        deactivate: bool = True,
    ) -> None:
        """Register an event callback that reclaims a particle to the pool.

        The registered callback calls `reclaim()` when `character` triggers
        `event` for `caller`. This is useful for particles whose lifecycle is
        naturally owned by a scene or path, such as smoke that should return to
        the pool when its fade scene completes.

        The callback registration itself is stored on the particle's
        `event_handler`. If future acquisitions use `ParticleReset` with
        `clear_events=True`, the reclaim callback is removed and must be
        registered again before it can fire.

        Args:
            character: Particle character that should be reclaimed.
            caller: Scene, path, or caller ID whose completion event should
                trigger reclamation.
            event: Event to listen for. Defaults to scene completion.
            hide: Passed to `reclaim()` when the callback fires.
            deactivate: Passed to `reclaim()` when the callback fires.

        """

        def reclaim(completed_character: EffectCharacter, *_: typing.Any) -> None:
            self.reclaim(completed_character, hide=hide, deactivate=deactivate)

        character.event_handler.register_event(
            event,
            caller,
            EventHandler.Action.CALLBACK,
            EventHandler.Callback(reclaim),
        )

    def extend(self, particles: Iterable[EffectCharacter]) -> None:
        """Add existing helper characters to the pool as available particles.

        This method adopts characters that were created elsewhere and makes them
        available for future reuse. It does not hide, deactivate, reset, or run
        the pool initializer on those characters; callers should prepare them
        before extending the pool if that state matters.

        Args:
            particles: Existing `EffectCharacter` instances to track and make
                available.

        """
        for particle in particles:
            self.particles.append(particle)
            self.available.append(particle)
