"""The TTE theme and title for the TUI.

TerminalTextEffects' colors are purple `8A008A`, cyan `00D1FF`, and white. The theme uses purple for panels and
buttons, cyan for focus and highlights, and a purple-tinted dark background. The title is drawn with a gradient
through the three colors, built with TTE's own `Gradient`.
"""

from __future__ import annotations

from rich.style import Style
from rich.text import Text
from textual.theme import Theme

from terminaltexteffects.utils.graphics import Color, Gradient

PURPLE = "#8A008A"
CYAN = "#00D1FF"
WHITE = "#FFFFFF"

TTE_THEME = Theme(
    name="tte",
    primary=PURPLE,
    secondary=CYAN,
    accent=CYAN,
    foreground="#EEE8F2",
    background="#110C16",
    surface="#19121F",
    panel="#251A2D",
    warning="#FFB454",
    error="#FF5C8A",
    success="#5FE0A0",
    dark=True,
    variables={
        "block-cursor-background": CYAN,
        "block-cursor-foreground": "#110C16",
        "footer-key-foreground": CYAN,
        "input-selection-background": f"{PURPLE} 50%",
        "border": CYAN,
        "block-hover-background": f"{PURPLE} 55%",
    },
)
"""Textual theme in TTE's purple, cyan, and white."""


def gradient_text(text: str, *, bold: bool = True) -> Text:
    """Return `text` colored with a purple, cyan, and white gradient across its characters."""
    stops = (Color(PURPLE[1:]), Color(CYAN[1:]), Color(WHITE[1:]))
    gradient = Gradient(*stops, steps=max(1, len(text) // 2))
    result = Text()
    for index, character in enumerate(text):
        color = gradient.get_color_at_fraction(index / max(1, len(text) - 1))
        result.append(character, Style(color=f"#{color.rgb_color}", bold=bold))
    return result
