# Scene

*Module*: `terminaltexteffects.engine.animation`

Set `cache_easing=True` when constructing a scene (directly or through `Animation.new_scene`) to reuse
frame-index schedules across scenes with the same built-in easing function and frame durations.
Each scene keeps its own frames, visuals, playback cursor, and lifecycle events. The default is `False`.

The shared cache retains at most 32 schedules, with at most 4096 ticks per schedule. Scenes hold weak
references so eviction can release a schedule; playback reacquires it when needed. Assigning a different
`ease` or adding frames selects a new schedule. Resetting or looping reuses the existing layout.
Custom easing functions, longer scenes, and motion-synced scenes keep their ordinary playback behavior.
Opt in after measuring an effect: distinct layouts, short playback, and frequent eviction can cost more
than schedule reuse saves.

::: terminaltexteffects.engine.animation.Scene
