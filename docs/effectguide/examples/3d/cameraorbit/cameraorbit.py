"""A moving camera circles a stationary cube carrying the input text."""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.space3d import Cube, Shaded, Space3D
from terminaltexteffects.utils import argutils, easing


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
        self.space = Space3D(self.terminal)
        self.cube = self.space.body(Cube(48)).draw(Shaded())
        characters = self.terminal.get_characters()
        anchors = [self.cube.anchor(a.point.x, a.point.y, 24, normal="z") for a in self.cube.text_plane(characters)]
        self.cube.add_chars(characters, anchors, blend_frames=0, hide_when_facing_away=True)
        for character in characters:
            self.terminal.set_character_visibility(character, is_visible=True)
            self.active_characters.add(character)
        self.space.camera.set_position(0, 20, 170).look_at(self.cube).zoom(1.4)
        self.space.camera.orbit("y", turns=1, around=self.cube, frames=360, ease=easing.in_out_sine)
        self.finished = False

    def __next__(self) -> str:
        """Orbit once, then release the text back to its input cells."""
        if self.space.animating:
            self.space.step()
        elif not self.finished:
            self.cube.release_all()
            self.cube.erase()
            self.space.step()
            for character in self.terminal.get_characters():
                character.motion.set_coordinate(character.input_coord)
                self.terminal.set_character_visibility(character, is_visible=True)
            self.finished = True
        else:
            raise StopIteration
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
