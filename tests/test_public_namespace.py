"""The 3D names effects use are reachable from the top-level package."""

from __future__ import annotations

import pytest

import terminaltexteffects as tte
from terminaltexteffects.engine import drawing, shapes, tweens, world
from terminaltexteffects.utils import geometry3d

pytestmark = [pytest.mark.engine, pytest.mark.smoke]


def test_shapes_and_looks_are_top_level() -> None:
    """`tte.shapes` is the engine's shapes module, and every public look sits on `tte` as the engine's own class."""
    assert tte.shapes is shapes
    assert all(getattr(tte, name) is getattr(drawing, name) for name in drawing.__all__)


def test_core_3d_names_are_top_level() -> None:
    """The vector, rotation and body types sit beside `Coord` and `Color`."""
    assert tte.Vec3 is geometry3d.Vec3
    assert tte.Rotation is geometry3d.Rotation
    assert tte.rotation_about is tweens.rotation_about
    assert tte.Body is world.Body
