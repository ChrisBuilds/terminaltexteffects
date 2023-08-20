from dataclasses import dataclass, field
from terminaltexteffects.utils import ansitools
from terminaltexteffects.utils import colorterm


@dataclass
class GraphicalEffect:
    """A class for storing terminal graphical modes and a color.

    Supported graphical modes:
    bold, dim, italic, underline, blink, inverse, hidden, strike

    Args:
        bold (bool): bold mode
        dim (bool): dim mode
        italic (bool): italic mode
        underline (bool): underline mode
        blink (bool): blink mode
        reverse (bool): reverse mode
        hidden (bool): hidden mode
        strike (bool): strike mode
        color (int): color code
    """

    bold: bool = False
    dim: bool = False
    italic: bool = False
    underline: bool = False
    blink: bool = False
    reverse: bool = False
    hidden: bool = False
    strike: bool = False
    color: int = 0

    def disable_modes(self) -> None:
        """Disables all graphical modes."""
        self.bold = False
        self.dim = False
        self.italic = False
        self.underline = False
        self.blink = False
        self.reverse = False
        self.hidden = False
        self.strike = False


@dataclass
class AnimationUnit:
    """An AnimationUnit is a graphicaleffect with a symbol and duration. May be looping.

    Args:
        symbol (str): the symbol to show
        duration (int): the number of animation steps to use the AnimationUnit
        is_looping (bool): if True, the AnimationUnit will be recycled until the character reaches its final position
        graphical_effect (GraphicalEffect): a GraphicalEffect object containing the graphical modes and color of the character
    """

    symbol: str
    duration: int
    is_looping: bool = False
    graphical_effect: GraphicalEffect = field(default_factory=GraphicalEffect)

    def __post_init__(self):
        self.frames_played = 0
        self.format_symbol()

    def format_symbol(self) -> None:
        """Formats the symbol for printing."""
        formatting_string = ""
        if self.graphical_effect.bold:
            formatting_string += ansitools.APPLY_BOLD()
        if self.graphical_effect.italic:
            formatting_string += ansitools.APPLY_ITALIC()
        if self.graphical_effect.underline:
            formatting_string += ansitools.APPLY_UNDERLINE()
        if self.graphical_effect.blink:
            formatting_string += ansitools.APPLY_BLINK()
        if self.graphical_effect.reverse:
            formatting_string += ansitools.APPLY_REVERSE()
        if self.graphical_effect.hidden:
            formatting_string += ansitools.APPLY_HIDDEN()
        if self.graphical_effect.strike:
            formatting_string += ansitools.APPLY_STRIKETHROUGH()
        if self.graphical_effect.color:
            formatting_string += colorterm.fg(self.graphical_effect.color)

        self.symbol = f"{formatting_string}{self.symbol}{ansitools.RESET_ALL() if formatting_string else ''}"
