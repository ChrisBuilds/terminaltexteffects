"""How a character is seen: its cell, depth, which way its surface faces, and how lit it is.

    view = character.view
    if view.facing:
        character.animation.set_appearance(symbol, gradient.get_color_at_fraction(view.light))

Readings are worked out on the first read after the world steps, from the character's place in the world, the
camera and the light, so they work for any character on any body.

Classes:
    View: The readings for one character.
"""

from __future__ import annotations

import typing

from terminaltexteffects.utils import geometry3d as g3

if typing.TYPE_CHECKING:
    from terminaltexteffects.engine.base_character import EffectCharacter
    from terminaltexteffects.engine.surfaces import FaceName
    from terminaltexteffects.utils.geometry import Coord

__all__ = ["View"]

_EPSILON = 1e-9


class View:
    """How a character is seen from the camera, read through `character.view`.

    Readings follow the character's surface: the outward normal of its parent's surface where it sits. A character
    on a body without a surface, free in the world or on `world.screen` has no normal, so it counts as facing the
    camera and fully lit.

    Attributes:
        cell (Coord): The cell the character projects onto.
        depth (float): Distance from the eye along the camera's view axis, in units. Smaller is nearer.
        nearness (float): 1 at the nearest point its parent body reaches at its size, 0 at the farthest.
        facing (bool): Whether its surface faces the camera.
        facing_amount (float): -1 facing directly away, 0 edge-on, 1 facing the camera.
        light (float): How directly its surface faces the light, from 0 to 1.
        face (str | int | None): The face of its parent's surface it is on, as `surface.face()` takes it, or `None`
            off a surface or on one without faces.
        projected (bool): Whether the character is in front of the camera's near plane. While it isn't, it is
            hidden and the other readings keep their last values.

    """

    __slots__ = (
        "_cell",
        "_character",
        "_depth",
        "_face",
        "_facing_amount",
        "_key",
        "_light",
        "_nearness",
        "_projected",
    )

    def __init__(self, character: EffectCharacter) -> None:
        """Create the readings for a character. Use `character.view`."""
        self._character = character
        self._key: object = None
        self._projected = True
        self._cell: Coord = character.motion.current_coord
        self._depth = 0.0
        self._nearness = 1.0
        self._facing_amount = 1.0
        self._light = 1.0
        self._face: FaceName | None = None

    @property
    def cell(self) -> Coord:
        """The cell the character projects onto."""
        self._refresh()
        return self._cell

    @property
    def depth(self) -> float:
        """Distance from the eye along the camera's view axis, in units. Smaller is nearer."""
        self._refresh()
        return self._depth

    @property
    def nearness(self) -> float:
        """1 at the nearest point its parent body reaches at its size, 0 at the farthest."""
        self._refresh()
        return self._nearness

    @property
    def facing(self) -> bool:
        """Whether its surface faces the camera."""
        self._refresh()
        return self._facing_amount > 0

    @property
    def facing_amount(self) -> float:
        """-1 facing directly away, 0 edge-on, 1 facing the camera."""
        self._refresh()
        return self._facing_amount

    @property
    def light(self) -> float:
        """How directly its surface faces the light, from 0 to 1."""
        self._refresh()
        return self._light

    @property
    def face(self) -> FaceName | None:
        """The face of its parent's surface it is on, or `None`."""
        self._refresh()
        return self._face

    @property
    def projected(self) -> bool:
        """Whether the character is in front of the camera's near plane."""
        self._refresh()
        return self._projected

    def _refresh(self) -> None:
        """Work the readings out again if the world stepped or the character moved since they were."""
        character = self._character
        motion = character.motion
        parent = character.parent
        world = parent.world
        key = (world._frame, parent, motion._xyz, motion.current_coord)
        if self._key == key:
            return
        self._key = key
        camera = world.camera
        if parent._screen:
            # On the screen: on its cell, at the text plane's depth, facing the camera in full light.
            self._projected = True
            self._cell = motion.current_coord
            self._depth = camera.distance
            self._nearness = self._facing_amount = self._light = 1.0
            self._face = None
            return
        position = motion.position
        point = parent.to_world(position)
        projected = camera.project(point)
        self._projected = projected is not None
        if projected is None:
            return
        self._cell = motion.current_coord
        self._depth = projected.depth
        reach = parent._reach()
        if reach > _EPSILON:
            center = camera.depth(parent.world_position)
            self._nearness = min(max((center + reach - projected.depth) / (2 * reach), 0.0), 1.0)
        else:
            self._nearness = 1.0
        surface = parent._surface
        if surface is None:
            self._facing_amount = 1.0
            self._light = 1.0
            self._face = None
            return
        xyz = surface._normalize((position.x, position.y, position.z))
        normal = parent._world_normal(surface._normal(xyz))
        self._facing_amount = normal.dot(camera.view_direction(point))
        self._light = g3.lambert(normal, world.world_light)
        self._face = surface._face_at(xyz)
