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

## Encoded appearance reuse

Set `cache_appearance=True` on `Scene` or `Animation.new_scene` to reuse immutable ANSI strings when
constructing frames with repeated symbols, styles, and resolved foreground/background colors. The option
defaults to `False`. Frames, visuals, colors and playback state retain their usual independent ownership;
editing a visual's formatted string still invalidates terminal output. Explicit `format_symbol()` calls
retain ordinary formatting.

The shared LRU holds at most 2048 encodings. Existing visuals retain their strings after eviction.
Subclass/formatter overrides and custom style or color-code values use the ordinary path. Unicode symbol
validation and width calculation remain unchanged. Color policy is applied before selecting an encoding,
including preexisting colors/bold, XTerm conversion and no-color output.

Waves enables this option only for its repeated wave scene. Measure construction time and allocation before
enabling it elsewhere: lookup overhead can outweigh reuse when appearances vary.
