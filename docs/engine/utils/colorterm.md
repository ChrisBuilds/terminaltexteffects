# ColorTerm

*Module*: `terminaltexteffects.utils.colorterm`

!!! info "New in 0.16.0"

    `reset_fg()` and `reset_bg()` are available on development `main` and are not in the published 0.15.0 package.

Use `reset_fg()` to restore the terminal's default foreground color, or `reset_bg()` to restore its default background
color. Each emits a selective SGR reset and leaves the other color and text attributes in effect. Use
`ansitools.reset_all()` to clear all formatting.

::: terminaltexteffects.utils.colorterm
