"""MySpin, tutorial step 4: shading and the back side.

Each character's color follows how squarely it faces the light in front of the sheet: dark when edge-on or turned
away, its gradient color facing forward. Later steps build it up into the Spin effect.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import Color, ColorPair, EffectCharacter, Gradient, Scene, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.space3d import Body, Space3D
from terminaltexteffects.utils import argutils

START_DISTANCE = 200
"""How far behind the canvas the sheet starts, in columns."""

SPIN_FRAMES = 240
"""Frames from the start until the sheet lands."""

SHADOW_COLOR = Color("#303030")
"""Color of the text when it faces away from the light."""

FINAL_GRADIENT = Gradient(Color("#8A008A"), Color("#00D1FF"), Color("#FFFFFF"), steps=12)
"""Colors of the text facing the light, top to bottom."""

HIDE_BACK = False
"""Whether to hide the text while its back faces the viewer, instead of showing it mirrored in shadow."""


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "myspin", MySpin, MySpinConfig


@dataclass
class MySpinConfig(BaseConfig):
    """Configuration for the MySpin effect. It has no options yet."""

    parser_spec = argutils.ParserSpec(
        name="myspin",
        help="The text tumbles in from the distance as a flat sheet, spins, and settles into place.",
        description="myspin | The text tumbles in from the distance as a flat sheet, spins, and settles into place.",
        epilog="Example: tte myspin",
    )


class MySpinIterator(BaseEffectIterator[MySpinConfig]):
    """Produce the frames of the MySpin effect."""

    def __init__(self, effect: MySpin) -> None:
        """Mount the text on a sheet far behind the canvas and queue its approach."""
        super().__init__(effect)
        self.final_colors: dict[EffectCharacter, ColorPair] = {}
        self.space = Space3D(self.terminal, perspective=1, light="front")
        self.build()

    def build(self) -> None:
        """Shade and mount every visible character, move the sheet back, and queue the spin and approach."""
        final_gradient_mapping = FINAL_GRADIENT.build_coordinate_color_mapping(
            self.terminal.canvas.text_bottom,
            self.terminal.canvas.text_top,
            self.terminal.canvas.text_left,
            self.terminal.canvas.text_right,
            Gradient.Direction.VERTICAL,
        )
        characters = [character for character in self.terminal.get_characters() if character.input_symbol != " "]
        for character in characters:
            final_color = final_gradient_mapping[character.input_coord]
            self.final_colors[character] = ColorPair(fg=final_color)
            # The mount's light reading picks the frame: shadow when the text faces away, the final color facing
            # the light.
            scene = character.animation.new_scene(sync=Scene.SyncMetric.LIGHT)
            scene.apply_gradient_to_symbols(
                character.input_symbol, 1, fg_gradient=Gradient(SHADOW_COLOR, final_color, steps=10)
            )
            character.animation.activate_scene(scene)
            self.terminal.set_character_visibility(character, is_visible=True)
            self.active_characters.add(character)
        self.sheet = self.space.body()
        self.sheet.add_chars(characters, self.sheet.text_plane(characters), hide_when_facing_away=HIDE_BACK)
        # The anchors are placed for the sheet's pose at rest, so move the sheet after mounting.
        self.sheet.set_position(0, 0, -START_DISTANCE)
        self.sheet.spin("y", turns=2, frames=SPIN_FRAMES, ease=easing.out_cubic)
        self.sheet.move_to(0, 0, 0, frames=SPIN_FRAMES, ease=easing.out_cubic, together=True)
        self.sheet.on_complete(self.finish)

    def finish(self, sheet: Body) -> None:
        """Hand the characters back, on their input cells, and show them in their final colors."""
        sheet.release_all()
        for character, colors in self.final_colors.items():
            character.animation.deactivate_scene()
            character.animation.set_appearance(character.input_symbol, colors)

    def __next__(self) -> str:
        """Move the sheet one frame, then the characters with it."""
        if self.space.animating or self.active_characters:
            self.space.step()
            self.update()
            return self.frame
        raise StopIteration


class MySpin(BaseEffect[MySpinConfig]):
    """The text tumbles in from the distance as a flat sheet, spins, and settles into place."""

    @property
    def _config_cls(self) -> type[MySpinConfig]:
        return MySpinConfig

    @property
    def _iterator_cls(self) -> type[MySpinIterator]:
        return MySpinIterator
