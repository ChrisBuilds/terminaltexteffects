# Animation

*Module*: `terminaltexteffects.engine.animation`

## Appearance Reuse

!!! info "New in 0.16.0"

    `set_appearance_if_changed()` is available on development `main` and is not in the published 0.15.0 package.

`Animation.set_appearance_if_changed(symbol=None, colors=None)` follows the ordinary setter's symbol defaults,
color overrides, and width tracking. It reuses its last visual when the effective request, color policy, visual
identity, and all visual instance fields remain unchanged. Scene stepping, an ordinary setter call, or direct
style, color-code, width, or formatted-symbol edits force the next helper call to reapply the requested appearance.
The helper does not stop an active scene from overwriting that appearance on its next step.

The snapshot is allocated lazily for each animation using the helper. It retains one visual and field snapshot;
visuals are not shared across characters. Callers should not rely on receiving a new visual object each call; use
`Animation.set_appearance()` when a fresh visual is required.

For input-derived characters in `existing_color_handling="always"` mode, the helper ignores requested colors in the
comparison because parsed input colors override them. Helper characters without input-color ownership still compare
the requested colors.

Opt in only after measuring (see [Performance Testing](../../performance.md)): comparing and retaining snapshots can
cost more than it saves when effective appearances change frequently. Overflow row coloring and Spotlights use the
helper only in `always` mode.

## Animation Reference

::: terminaltexteffects.engine.animation.Animation
