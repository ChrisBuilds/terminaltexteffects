"""Glow: characters slide home while a scene heats them from a red spark to white text.

An Effect Guide example for the Animation chapter.
"""

from __future__ import annotations

import typing
from dataclasses import dataclass

from terminaltexteffects import Color, Coord, Gradient, Scene, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils

SYNC_METRICS = {"none": None, "distance": Scene.SyncMetric.DISTANCE, "step": Scene.SyncMetric.STEP}


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "glow", Glow, GlowConfig


@dataclass
class GlowConfig(BaseConfig):
    """Configuration for the Glow effect."""

    parser_spec = argutils.ParserSpec(
        name="glow",
        help="Characters slide home, heating from a red spark to white text.",
        description="glow | Characters slide home, heating from a red spark to white text.",
        epilog="Example: tte glow --sync distance",
    )
    frame_duration: int = argutils.ArgSpec(
        name="--frame-duration",
        type=argutils.PositiveInt.type_parser,
        default=3,
        metavar=argutils.PositiveInt.METAVAR,
        help="Ticks to show each frame of the scene. Ignored when the scene is synced.",
    )  # pyright: ignore[reportAssignmentType]
    "int : Ticks to show each frame of the scene. Ignored when the scene is synced."

    sync: typing.Literal["none", "distance", "step"] = argutils.ArgSpec(
        name="--sync",
        default="none",
        choices=["none", "distance", "step"],
        help="Sync the scene to the character's path.",
    )  # pyright: ignore[reportAssignmentType]
    "typing.Literal['none', 'distance', 'step'] : Sync the scene to the character's path."


class GlowIterator(BaseEffectIterator[GlowConfig]):
    """Produce the frames of the Glow effect."""

    def __init__(self, effect: Glow) -> None:
        """Give every character a path home and a scene, and start both."""
        super().__init__(effect)
        heat = Gradient(Color("#ff2000"), Color("#ffc000"), Color("#ffffff"), steps=6)
        for character in self.terminal.get_characters():
            character.motion.set_coordinate(Coord(self.terminal.canvas.left, character.input_coord.row))
            path = character.motion.new_path(speed=0.5, ease=easing.out_expo)
            path.new_waypoint(character.input_coord)
            character.motion.activate_path(path)

            scene = character.animation.new_scene(sync=SYNC_METRICS[self.config.sync])
            scene.apply_gradient_to_symbols(
                (".", "o", "O", character.input_symbol),
                self.config.frame_duration,
                fg_gradient=heat,
            )
            character.animation.activate_scene(scene)

            self.terminal.set_character_visibility(character, is_visible=True)
            self.active_characters.add(character)

    def __next__(self) -> str:
        """Advance every character one tick and return the frame."""
        if self.active_characters:
            self.update()
            return self.frame
        raise StopIteration


class Glow(BaseEffect[GlowConfig]):
    """Characters slide home, heating from a red spark to white text."""

    @property
    def _config_cls(self) -> type[GlowConfig]:
        return GlowConfig

    @property
    def _iterator_cls(self) -> type[GlowIterator]:
        return GlowIterator
