# ParticlePool

*Module*: `terminaltexteffects.engine.effect_support.particles`

!!! info "New in 0.16.0"

    `ParticlePool` and `ParticleReset` are available on development `main` and are not in the published 0.15.0
    package.

`ParticlePool` reuses helper characters for short-lived visuals such as sparks, smoke, or fragments. The pool creates
characters with `Terminal.add_character()`, shows and activates them when emitted, and returns them to the pool when
they are reclaimed. Particles remain ordinary `EffectCharacter` objects, so the effect configures their scenes, paths,
and events with the usual APIs.

Use the `initializer` callback for setup that survives reuse, such as building scenes and registering a reclaim event.
Use the callback passed to `emit()` for per-emission setup, such as paths and scene resets. `ParticleReset` selects
which state is cleared each time a particle is reused; by default, paths are cleared and any active path or scene is
deactivated, while scenes and event registrations are kept.

The following snippet runs inside an effect iterator, where `self.terminal` and `self.active_characters` are available:

```python
from terminaltexteffects import Coord, EffectCharacter, ParticlePool


def initialize_spark(particle: EffectCharacter) -> None:
    scene = particle.animation.new_scene(scene_id="spark")
    for symbol in "*+.":
        scene.add_frame(symbol, 4)
    self.sparks.reclaim_on_event(particle, caller=scene)  # (1)


self.sparks = ParticlePool(
    self.terminal,
    self.active_characters,
    "*",
    max_size=32,
    initializer=initialize_spark,
)


def launch(particle: EffectCharacter) -> None:
    scene = particle.animation.query_scene("spark")
    scene.reset_scene()
    path = particle.motion.new_path(speed=0.5)
    path.new_waypoint(Coord(origin.column, origin.row + 3))
    particle.motion.activate_path(path)
    particle.animation.activate_scene(scene)


self.sparks.emit(origin, launch)  # (2)
```

1. Returns the particle to the pool when its scene completes. Registering it in the initializer keeps the
   registration across reuse.
2. Returns `None` instead of a particle when every particle is in use and the pool has reached `max_size`.

::: terminaltexteffects.engine.effect_support.particles
