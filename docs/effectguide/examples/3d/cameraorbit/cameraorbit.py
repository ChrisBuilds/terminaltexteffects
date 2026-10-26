"""A moving camera circles a stationary cube carrying the input text."""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import Color, ColorPair, Gradient
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.drawing import Solid
from terminaltexteffects.engine.shapes import Cube
from terminaltexteffects.utils import argutils, easing
from terminaltexteffects.utils.geometry import Coord


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect and configuration classes."""
    return "cameraorbit", CameraOrbit, CameraOrbitConfig


@dataclass
class CameraOrbitConfig(BaseConfig):
    """Configuration for the CameraOrbit guide example."""

    parser_spec = argutils.ParserSpec(
        name="cameraorbit",
        help="A camera circles a stationary cube carrying text.",
        description="cameraorbit | A camera circles a stationary cube carrying text.",
        epilog="Example: tte --canvas-width 80 --canvas-height 32 --anchor-text c cameraorbit",
    )


class CameraOrbitIterator(BaseEffectIterator[CameraOrbitConfig]):
    """Keep the cube still and animate only the camera."""

    def __init__(self, effect: CameraOrbit) -> None:
        """Place text on the cube's front face and queue a complete orbit."""
        super().__init__(effect)
        self.world = self.terminal.world
        # A quiet surface lets the letters on it carry the detail.
        self.cube = self.world.body(Cube(48)).draw(Solid(gradient=Gradient(Color("132432"), Color("247b91"), steps=12)))
        for x, z in ((-30, -15), (30, -15), (0, 32)):
            self.world.body(Cube(4), at=(x, -23, z)).draw(
                Solid(gradient=Gradient(Color("493522"), Color("e4ac59"), steps=8))
            )
        self.labels = []
        title = "CAMERA ORBIT: cube and gold landmarks stay still"
        start = self.terminal.canvas.center.column - len(title) // 2
        for offset, symbol in enumerate(title):
            coord = Coord(start + offset, self.terminal.canvas.top)
            label = self.terminal.add_character(symbol, coord)
            # On the screen, the title stays on its cells while the camera moves. A high layer keeps it in front.
            label.attach(self.world.screen, at=coord)
            label.layer = 10_000
            label.animation.set_appearance(symbol, ColorPair(fg=Color("d9e5ef")))
            self.terminal.set_character_visibility(label, is_visible=True)
            self.labels.append(label)
        characters = self.terminal.get_characters()
        self.cube.surface.face("front").layout_text(characters)
        self.cube.hide_facing_away = True
        for character in characters:
            self.terminal.set_character_visibility(character, is_visible=True)
            self.active_characters.add(character)
        self.world.camera.set_position(0, 20, 170).look_at(self.cube).zoom(1.25)
        self.world.camera.orbit("y", turns=1, around=self.cube, frames=360, ease=easing.in_out_sine)
        self.finished = False

    def __next__(self) -> str:
        """Orbit once, then put the text back on its input cells."""
        if not self.world.animating:
            if self.finished:
                raise StopIteration
            for body in self.world.bodies:
                self.world.remove(body)  # Its cells are hidden when the world next paints.
            for label in self.labels:
                self.terminal.set_character_visibility(label, is_visible=False)
            self.world.camera.reset()
            for character in self.terminal.get_characters():
                character.attach(self.world.text_plane, at=character.input_coord)
                self.terminal.set_character_visibility(character, is_visible=True)
            self.finished = True
        self.update()
        return self.frame


class CameraOrbit(BaseEffect[CameraOrbitConfig]):
    """A camera circles a stationary cube carrying text."""

    @property
    def _config_cls(self) -> type[CameraOrbitConfig]:
        return CameraOrbitConfig

    @property
    def _iterator_cls(self) -> type[CameraOrbitIterator]:
        return CameraOrbitIterator
