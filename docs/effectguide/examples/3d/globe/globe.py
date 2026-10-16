"""Globe: the input text wrapped around a turning sphere, with the far side showing through.

An Effect Guide recipe.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.space3d import Space3D, Sphere, Textured
from terminaltexteffects.utils import argutils


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "globe", Globe, GlobeConfig


@dataclass
class GlobeConfig(BaseConfig):
    """Configuration for the Globe effect."""

    parser_spec = argutils.ParserSpec(
        name="globe",
        help="The input text wrapped around a turning sphere.",
        description="globe | The input text wrapped around a turning sphere.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c globe",
    )


class GlobeIterator(BaseEffectIterator[GlobeConfig]):
    """Produce the frames of the Globe effect."""

    def __init__(self, effect: Globe) -> None:
        """Wrap the input text around a sphere and turn it."""
        super().__init__(effect)
        self.space = Space3D(self.terminal)
        # More segments and rings make a rounder outline. back="dim" shows the far side through the text's spaces.
        globe = self.space.body(Sphere(radius=20, segments=48, rings=24)).draw(Textured(back="dim"))
        globe.rotate("z", -15).rotate("x", 15)
        globe.spin("y", turns=1, frames=480, ease=easing.in_out_sine, local=True)
        self.text_shown = False

    def __next__(self) -> str:
        """Turn the globe, then swap it for the text."""
        if self.space.animating:
            self.space.step()
        elif not self.text_shown:
            for body in self.space.bodies:
                body.erase()
            self.space.step()  # Hides the surface characters once nothing is drawn.
            for character in self.terminal.get_characters():
                self.terminal.set_character_visibility(character, is_visible=True)
            self.text_shown = True
        else:
            raise StopIteration
        self.update()
        return self.frame


class Globe(BaseEffect[GlobeConfig]):
    """The input text wrapped around a turning sphere."""

    @property
    def _config_cls(self) -> type[GlobeConfig]:
        return GlobeConfig

    @property
    def _iterator_cls(self) -> type[GlobeIterator]:
        return GlobeIterator
