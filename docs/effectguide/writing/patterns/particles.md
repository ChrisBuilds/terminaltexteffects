# Particles

Sparks, smoke, debris, and rain aren't part of the input text. Effects draw them with **particles**: extra characters
that appear, play a short animation, and disappear, often many times over. [`ParticlePool`](../../../engine/particles.md)
creates these characters and reuses them, so an effect can emit thousands of particles while only a few dozen exist at
once. Built-in effects that use particles include Burn, Laseretch, and Thunderstorm.

## The Sparks example

Sparks reveals the text one column at a time, from left to right. Every character throws off a spark that flies up and
fades from a white `*` through a yellow `+` to an orange `.`. Save it as `sparks.py` in your community effects
directory:

```python title="sparks.py"
--8<-- "docs/effectguide/examples/sparks/sparks.py"
```

```bash
tte --input-file concept_input.txt sparks
```

![Columns of text appear from left to right, throwing off sparks that rise and fade](../../../img/effectguide/sparks_demo.webp)

## How the pool works

A particle is an ordinary `EffectCharacter` created with `terminal.add_character()`, so it has paths, scenes, and
events like any other character (see [Added characters](../../engine/characters.md#added-characters)). The pool keeps
track of which particles are in use and which are free.

`ParticlePool(terminal, active_characters, symbols, ...)` takes the iterator's `active_characters`, because emitting
and reclaiming add particles to it and remove them from it. Its other arguments:

| Argument | Use |
| --- | --- |
| `symbols` | The symbol for new particles, or several to choose from at random. |
| `max_size` | The most particles the pool creates. `None`, the default, has no limit. |
| `initial_count` | How many particles to create up front, instead of when first needed. |
| `initializer` | A function run once for each new particle. |

Setup is split between two functions:

- The **initializer** runs once per particle. Sparks uses it for everything that stays the same between uses: the
  layer, the fade scene, and the event that returns the particle to the pool.
- The **emit callback** runs on every use. Sparks's `launch_spark()` gives the spark a new path, resets its scene to
  the first frame, and activates it.

`emit(origin, callback)` takes a free particle, or creates one, moves it to `origin`, calls the callback, makes it
visible, and adds it to `active_characters`. When a particle is reused, the pool first clears its old paths and stops
its path and scene; its scenes and events are kept. Pass `reset=ParticleReset(...)` to `emit()` to clear more or less.

`reclaim_on_event(particle, caller=scene)` returns the particle to the pool when its scene completes: it is hidden,
removed from `active_characters`, and becomes free again. Without a reclaim, a particle stays in use for the rest of
the effect.

## When the pool is full

When every particle is in use and the pool has reached `max_size`, `emit()` returns `None` and emits nothing. Sparks
ignores the result, so characters revealed while the pool is full throw no spark. With a small pool, the effect has
fewer sparks on screen:

```bash
tte --input-file concept_input.txt sparks --max-sparks 8
```

![Columns of text appear with only a few sparks at a time](../../../img/effectguide/sparks_few_demo.webp)

A cap keeps the cost of a frame predictable on large input, since every active particle is updated every tick. Choose
`max_size` from how many particles should be visible at once, not from the size of the text.

## Where to go next

- The [`ParticlePool` Reference](../../../engine/particles.md) lists every method, including `acquire()` for manual
  setup and `ParticleReset`.
- [Phases and staggered starts](phases.md) explains the column-by-column reveal.
