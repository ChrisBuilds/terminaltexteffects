"""The 3D names effects use are reachable from the top-level package."""

from __future__ import annotations

import pytest

import terminaltexteffects as tte
from terminaltexteffects import looks, shapes
from terminaltexteffects.engine import drawing, tweens, world
from terminaltexteffects.engine import shapes as engine_shapes
from terminaltexteffects.utils import geometry3d

pytestmark = [pytest.mark.engine, pytest.mark.smoke]


def test_shapes_and_looks_re_export_the_engine_classes() -> None:
    """`tte.shapes` and `tte.looks` list every public shape and look, as the engine's own classes."""
    assert tte.shapes is shapes
    assert tte.looks is looks
    assert shapes.__all__ == engine_shapes.__all__
    assert all(getattr(shapes, name) is getattr(engine_shapes, name) for name in engine_shapes.__all__)
    assert looks.__all__ == drawing.__all__
    assert all(getattr(looks, name) is getattr(drawing, name) for name in drawing.__all__)


def test_core_3d_names_are_top_level() -> None:
    """The vector, rotation and body types sit beside `Coord` and `Color`."""
    assert tte.Vec3 is geometry3d.Vec3
    assert tte.Rotation is geometry3d.Rotation
    assert tte.rotation_about is tweens.rotation_about
    assert tte.Body is world.Body
