"""Output contracts for shared 3D geometry preparation and immutable edge topology."""

from __future__ import annotations

import pytest

from terminaltexteffects.utils import geometry3d as g3

pytestmark = [pytest.mark.smoke]


@pytest.mark.parametrize("orthographic", [False, True])
@pytest.mark.parametrize("position", [g3.ORIGIN, g3.Vec3(0, 0, 116)])
def test_prepared_sides_match_independent_fills(*, orthographic: bool, position: g3.Vec3) -> None:
    """Sharing geometry preserves both buffers, including near clipping, UVs and viewport bounds."""
    mesh = g3.box(16, 16, 16)
    camera = g3.Camera(20, 10, orthographic=orthographic)
    rotation = g3.Rotation.about_x(0.3) * g3.Rotation.about_y(0.4)
    bounds = g3.Bounds(1, 40, 1, 20)
    front, back = g3._rasterize_sides(mesh, camera, rotation=rotation, scale=1.0, position=position, bounds=bounds)
    assert front == g3.rasterize(mesh, camera, rotation=rotation, position=position, bounds=bounds, cull="back")
    assert back == g3.rasterize(mesh, camera, rotation=rotation, position=position, bounds=bounds, cull="front")
    assert front is not back


def test_cached_topology_preserves_edge_order_and_returns_independent_lists() -> None:
    """Mutating a returned edge list cannot change the immutable mesh or its wireframe."""
    mesh = g3.torus(20, 8, 36, 18)
    expected = list(
        dict.fromkeys(
            (min(a, b), max(a, b))
            for face in mesh.faces
            for a, b in zip(face.indices, face.indices[1:] + face.indices[:1])
        )
    )
    camera = g3.Camera(0, 0, orthographic=True)
    before = g3.wireframe(mesh, camera)
    edges = mesh.edges()
    assert edges == expected
    edges.clear()
    assert mesh.edges() == expected
    assert g3.wireframe(mesh, camera) == before
