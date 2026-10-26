"""Logo: the input text spins like a sign, shaded by the light, and settles back into place.

An Effect Guide recipe.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import Color, ColorPair, Gradient, Scene, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.world import Body
from terminaltexteffects.utils import argutils


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "logo", Logo, LogoConfig


@dataclass
class LogoConfig(BaseConfig):
    """Configuration for the Logo effect."""

    parser_spec = argutils.ParserSpec(
        name="logo",
        help="The input text spins like a sign and settles back into place.",
        description="logo | The input text spins like a sign and settles back into place.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c logo",
    )


class LogoIterator(BaseEffectIterator[LogoConfig]):
    """Produce the frames of the Logo effect."""

    def __init__(self, effect: Logo) -> None:
        """Color the text by the light on the text plane, and queue the plane's spin."""
        super().__init__(effect)
        self.world = self.terminal.world
        self.world.set_light("front")
        self.sign = self.world.text_plane
        # Hide the text while its back faces the viewer.
        self.sign.hide_facing_away = True
        characters = [c for c in self.terminal.get_characters() if c.input_symbol != " "]
        shade = Gradient(Color("#3a003a"), Color("#8A008A"), Color("#00D1FF"), Color("#ffffff"), steps=10)
        for character in characters:
            # The light on its spot picks the frame, so the text brightens as it turns toward the light.
            scene = character.animation.new_scene(sync=Scene.SyncMetric.LIGHT)
            scene.apply_gradient_to_symbols(character.input_symbol, 1, fg_gradient=shade)
            character.animation.activate_scene(scene)
            self.terminal.set_character_visibility(character, is_visible=True)
            self.active_characters.add(character)

        self.sign.spin("y", turns=2, frames=200, ease=easing.in_sine)
        self.sign.settle("y", turns=1, frames=160, ease=easing.out_back)
        self.sign.on_complete(self.finish)

    def finish(self, sign: Body) -> None:
        """Put the sign back at rest and show the text in its input colors."""
        sign.reset()
        # "always" reapplies input colors by itself. "dynamic" needs them passed, and "ignore" leaves them off.
        dynamic = self.terminal.config.existing_color_handling == "dynamic"
        for character in self.terminal.get_characters():
            colors = None
            if dynamic:
                colors = ColorPair(fg=character.animation.input_fg_color, bg=character.animation.input_bg_color)
            character.animation.deactivate_scene()
            character.animation.set_appearance(character.input_symbol, colors)

    def __next__(self) -> str:
        """Spin the sign until it settles."""
        if self.world.animating or self.active_characters:
            self.update()
            return self.frame
        raise StopIteration


class Logo(BaseEffect[LogoConfig]):
    """The input text spins like a sign and settles back into place."""

    @property
    def _config_cls(self) -> type[LogoConfig]:
        return LogoConfig

    @property
    def _iterator_cls(self) -> type[LogoIterator]:
        return LogoIterator
