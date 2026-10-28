"""Nodes: the text plane tips back into a floor while a cube on an arm circles over it, then everything returns.

An Effect Guide example for The World chapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import easing, rotation_about
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.looks import Shaded
from terminaltexteffects.shapes import Cube
from terminaltexteffects.utils import argutils


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "nodes", Nodes, NodesConfig


@dataclass
class NodesConfig(BaseConfig):
    """Configuration for the Nodes effect."""

    parser_spec = argutils.ParserSpec(
        name="nodes",
        help="The text tips back into a floor while a cube on an arm circles over it.",
        description="nodes | The text tips back into a floor while a cube on an arm circles over it.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c nodes",
    )


class NodesIterator(BaseEffectIterator[NodesConfig]):
    """Produce the frames of the Nodes effect."""

    def __init__(self, effect: Nodes) -> None:
        """Show the text, build the arm and the cube, and queue the moves."""
        super().__init__(effect)
        self.world = self.terminal.world
        self.world.set_light("upper left")
        self.world.camera.set_perspective(2)  # Exaggerate depth, so the floor and the circle read as 3D.
        for character in self.terminal.get_characters():
            if character.input_symbol != " ":
                self.terminal.set_character_visibility(character, is_visible=True)

        # The text plane is a body like any other: tip it back into a floor, then stand it up again.
        floor = self.world.text_plane
        floor.hold(30)
        floor.turn_to(rotation_about("x", -70), frames=60, ease=easing.in_out_sine)
        floor.hold(240)
        floor.turn_to_rest(frames=60, ease=easing.in_out_sine)

        # An arm is a body with no shape: a pivot. The cube is its child, 26 units out along its x axis, so turning
        # the arm carries the cube round in a circle while the cube spins on its own.
        self.arm = self.world.body(at=(0, 6, 0))
        self.cube = self.world.body(Cube(8), at=(26, 0, 0), parent=self.arm).draw(Shaded())
        self.cube.scale = 0.01  # Scales must be positive: start too small to show.
        self.cube.hold(90).scale_to(1.0, frames=30, ease=easing.out_back)
        self.cube.spin("y", turns=3, frames=240, together=True)  # Starts with the scale-up.
        self.cube.scale_to(0.01, frames=30, ease=easing.in_back)
        self.arm.hold(90).spin("y", turns=1, frames=240, ease=easing.in_out_sine)

    def __next__(self) -> str:
        """Play until every body has finished, then remove the cube and its arm."""
        if not self.world.animating:
            if self.world.bodies:
                for body in self.world.bodies:
                    self.world.remove(body)
                self.update()
                return self.frame
            raise StopIteration
        self.update()
        return self.frame


class Nodes(BaseEffect[NodesConfig]):
    """The text tips back into a floor while a cube on an arm circles over it."""

    @property
    def _config_cls(self) -> type[NodesConfig]:
        return NodesConfig

    @property
    def _iterator_cls(self) -> type[NodesIterator]:
        return NodesIterator
