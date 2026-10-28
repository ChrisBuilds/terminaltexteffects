"""Shapes for bodies, gathered for effects: `tte.shapes.Cube(16)`, or `from terminaltexteffects.shapes import Cube`.

The classes are defined in `terminaltexteffects.engine.shapes`; this module re-exports its public names.

    cube = self.terminal.world.body(tte.shapes.Cube(16))

Classes:
    Shape: The base class for custom shapes.
    Plane: A flat rectangle facing +z, an open grid of cells like the text plane.
    Box, Cube, Prism, Pyramid, Cylinder, Sphere, Torus: Shapes with surfaces.
    Tetrahedron, Octahedron, Icosahedron: Shapes without surfaces yet.
"""

from __future__ import annotations

from terminaltexteffects.engine.shapes import (
    Box,
    Cube,
    Cylinder,
    Icosahedron,
    Octahedron,
    Plane,
    Prism,
    Pyramid,
    Shape,
    Sphere,
    Tetrahedron,
    Torus,
)

__all__ = [
    "Box",
    "Cube",
    "Cylinder",
    "Icosahedron",
    "Octahedron",
    "Plane",
    "Prism",
    "Pyramid",
    "Shape",
    "Sphere",
    "Tetrahedron",
    "Torus",
]
