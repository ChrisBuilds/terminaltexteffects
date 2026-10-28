"""Looks that `Body.draw` draws a body with: `tte.looks.Shaded()`, or `from terminaltexteffects.looks import Shaded`.

The classes are defined in `terminaltexteffects.engine.drawing`; this module re-exports the public ones.

    self.terminal.world.body(tte.shapes.Cube(16)).draw(tte.looks.Shaded())

Classes:
    Shaded: Fills faces with a symbol ramp and gradient by their angle to the light.
    Solid: Fills faces with one symbol.
    Textured: Wraps text over the faces.
    Wireframe: Draws the edges.

Types:
    Look: Any of the looks above.
"""

from __future__ import annotations

from terminaltexteffects.engine.drawing import Look, Shaded, Solid, Textured, Wireframe

__all__ = ["Look", "Shaded", "Solid", "Textured", "Wireframe"]
