"""Terminal Text Effects package.

This package provides various text effects for terminal applications.
"""

from terminaltexteffects.engine.animation import Animation, Scene
from terminaltexteffects.engine.base_character import EffectCharacter, EventHandler
from terminaltexteffects.engine.motion import (
    Motion,
    Path,
    Segment,
    Waypoint,
)
from terminaltexteffects.engine.terminal import Terminal
from terminaltexteffects.utils import easing, geometry
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.graphics import Color, ColorPair, Gradient

__version__ = "0.12.0"
