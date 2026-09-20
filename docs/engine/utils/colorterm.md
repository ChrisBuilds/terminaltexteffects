# ColorTerm

*Module*: `terminaltexteffects.utils.colorterm`

::: terminaltexteffects.utils.colorterm

Use `reset_fg()` to restore the terminal's default foreground color, or `reset_bg()` to restore its default background
color. Each emits a selective SGR reset and leaves the other color and text attributes in effect. Use
`ansitools.reset_all()` to clear all formatting.
