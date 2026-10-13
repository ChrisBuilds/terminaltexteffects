# Scene

*Module*: `terminaltexteffects.engine.animation`

## Opt-in Caches

!!! info "New in 0.16.0"

    `cache_easing` and `cache_appearance` are available on development `main` and are not in the published 0.15.0
    package.

Both options default to `False`. Opt in only after measuring an effect; each cache has overhead that can outweigh
its benefit. See [Performance Testing](../../performance.md) for the benchmark harness and a summary of the
measurements behind each cache.

### Eased-Scene Schedules

Set `cache_easing=True` when constructing a scene (directly or through `Animation.new_scene`) to reuse
frame-index schedules across scenes with the same built-in easing function and frame durations.
Each scene keeps its own frames, visuals, playback cursor, and lifecycle events.

The shared cache retains at most 32 schedules, with at most 4096 ticks per schedule. Scenes hold weak
references so eviction can release a schedule; playback reacquires it when needed. Assigning a different
`ease` or adding frames selects a new schedule. Resetting or looping reuses the existing layout.
Custom easing functions, longer scenes, and motion-synced scenes keep their ordinary playback behavior.
Distinct layouts, short playback, and frequent eviction can cost more than schedule reuse saves.

### Encoded Appearance Reuse

Set `cache_appearance=True` on `Scene` or `Animation.new_scene` to reuse immutable ANSI strings when
constructing frames with repeated symbols, styles, and resolved foreground/background colors.
Frames, visuals, colors, and playback state retain their usual independent ownership;
editing a visual's formatted string still invalidates terminal output. Explicit `format_symbol()` calls
retain ordinary formatting.

The shared LRU cache holds at most 2048 encodings. Existing visuals retain their strings after eviction.
Subclass/formatter overrides and custom style or color-code values use the ordinary path. Unicode symbol
validation and width calculation remain unchanged. Color policy is applied before selecting an encoding,
including preexisting colors/bold, XTerm conversion, and no-color output.
Lookup overhead can outweigh reuse when appearances vary.

Waves enables both options for its repeated wave scene.

## Scene Reference

::: terminaltexteffects.engine.animation.Scene
