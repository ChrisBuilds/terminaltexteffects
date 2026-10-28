"""Terminal Text Effects package.

This package provides various text effects for terminal applications.
"""

from terminaltexteffects import looks, shapes
from terminaltexteffects.engine.animation import Animation, Scene
from terminaltexteffects.engine.base_character import EffectCharacter, EventHandler
from terminaltexteffects.engine.effect_support import ParticlePool, ParticleReset
from terminaltexteffects.engine.motion import (
    Motion,
    Path,
    Segment,
    Waypoint,
)
from terminaltexteffects.engine.terminal import Terminal
from terminaltexteffects.engine.tweens import rotation_about
from terminaltexteffects.engine.world import Body
from terminaltexteffects.utils import easing, geometry, graphics
from terminaltexteffects.utils.argutils import CharacterOrder
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.geometry3d import Rotation, Vec3
from terminaltexteffects.utils.graphics import Color, ColorPair, Gradient

Event = EventHandler.Event
Action = EventHandler.Action
