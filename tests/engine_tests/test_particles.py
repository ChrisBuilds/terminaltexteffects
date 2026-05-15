"""Tests for engine particle pooling helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from terminaltexteffects.engine.effect_support.particles import ParticlePool, ParticleReset
from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.utils.geometry import Coord

if TYPE_CHECKING:
    from terminaltexteffects.engine.base_character import EffectCharacter

pytestmark = []


def make_terminal() -> Terminal:
    """Build a terminal with deterministic test-friendly configuration."""
    config = TerminalConfig._build_config()
    config.frame_rate = 0
    return Terminal("A", config=config)


def test_particle_pool_preallocates_hidden_available_characters() -> None:
    """Preallocation creates added helper characters and leaves them available."""
    terminal = make_terminal()
    active_characters: set[EffectCharacter] = set()

    pool = ParticlePool(terminal, active_characters, ".", initial_count=3, max_size=3)

    assert len(pool) == 3
    assert len(pool.available) == 3
    assert terminal.get_characters(added_chars=True, input_chars=False) == pool.particles
    assert all(not particle.is_visible for particle in pool.particles)
    assert not active_characters


def test_particle_emit_positions_shows_activates_and_runs_on_emit_callback() -> None:
    """Emitting a particle applies origin, on_emit callback, visibility, and active membership."""
    terminal = make_terminal()
    active_characters: set[EffectCharacter] = set()
    emitted: list[EffectCharacter] = []
    pool = ParticlePool(terminal, active_characters, ".", initial_count=1, max_size=1)

    def on_emit(particle: EffectCharacter) -> None:
        emitted.append(particle)
        path = particle.motion.new_path(speed=1)
        path.new_waypoint(Coord(2, 1))
        particle.motion.activate_path(path)

    particle = pool.emit(Coord(1, 1), on_emit)

    assert particle is not None
    assert particle.motion.current_coord == Coord(1, 1)
    assert particle.is_visible
    assert particle in active_characters
    assert emitted == [particle]


def test_particle_release_hides_deactivates_removes_and_returns_available() -> None:
    """Release returns a particle to the available collection."""
    terminal = make_terminal()
    active_characters: set[EffectCharacter] = set()
    pool = ParticlePool(terminal, active_characters, ".", initial_count=1, max_size=1)

    def on_emit(particle: EffectCharacter) -> None:
        scene = particle.animation.new_scene()
        scene.add_frame(".", duration=1)
        particle.animation.activate_scene(scene)

    particle = pool.emit(Coord(1, 1), on_emit)

    assert particle is not None
    pool.reclaim(particle)

    assert not particle.is_visible
    assert particle.animation.active_scene is None
    assert particle.motion.active_path is None
    assert particle not in active_characters
    assert particle in pool.available


def test_particle_capped_pool_returns_none_when_exhausted() -> None:
    """A capped pool skips emission after all particles are checked out."""
    terminal = make_terminal()
    active_characters: set[EffectCharacter] = set()
    pool = ParticlePool(terminal, active_characters, ".", initial_count=1, max_size=1)

    first_particle = pool.acquire()
    second_particle = pool.acquire()

    assert first_particle is not None
    assert second_particle is None


def test_particle_lazy_pool_creates_particles_on_demand() -> None:
    """A pool without a max size lazily creates particles."""
    terminal = make_terminal()
    active_characters: set[EffectCharacter] = set()
    pool = ParticlePool(terminal, active_characters, ".", initial_count=0)

    particle = pool.acquire()

    assert particle is not None
    assert len(pool) == 1
    assert terminal.get_characters(added_chars=True, input_chars=False) == [particle]


def test_particle_reclaim_on_scene_complete_returns_particle_to_pool() -> None:
    """Reclaim callbacks return particles after scene completion."""
    terminal = make_terminal()
    active_characters: set[EffectCharacter] = set()
    pool = ParticlePool(terminal, active_characters, ".", initial_count=1, max_size=1)

    def on_emit(particle: EffectCharacter) -> None:
        scene = particle.animation.new_scene(scene_id="flash")
        scene.add_frame(".", duration=1)
        pool.reclaim_on_event(particle, scene)
        particle.animation.activate_scene(scene)

    particle = pool.emit(Coord(1, 1), on_emit)

    assert particle is not None
    assert particle in active_characters
    particle.tick()

    assert not particle.is_visible
    assert particle.animation.active_scene is None
    assert particle not in active_characters
    assert particle in pool.available


def test_particle_acquire_reset_can_clear_paths_scenes_events_and_appearance() -> None:
    """Acquire reset flags clear selected reusable particle state."""
    terminal = make_terminal()
    active_characters: set[EffectCharacter] = set()
    pool = ParticlePool(terminal, active_characters, ".", initial_count=1, max_size=1)
    particle = pool.acquire()
    assert particle is not None
    particle.motion.new_path(path_id="old")
    old_scene = particle.animation.new_scene(scene_id="old")
    particle.event_handler.registered_events[(particle.event_handler.Event.SCENE_COMPLETE, old_scene)] = []
    particle.animation.set_appearance("x")
    pool.reclaim(particle, hide=False, deactivate=False)

    reacquired = pool.acquire(
        reset=ParticleReset(
            clear_paths=True,
            clear_scenes=True,
            clear_events=True,
            reset_appearance=True,
        ),
    )

    assert reacquired is particle
    assert not particle.motion.paths
    assert not particle.animation.scenes
    assert not particle.event_handler.registered_events
    assert particle.animation.current_character_visual.symbol == "."
