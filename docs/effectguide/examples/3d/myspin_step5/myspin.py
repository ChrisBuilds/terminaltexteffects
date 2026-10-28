"""MySpin, tutorial step 5: tumbling in and settling.

The sheet starts in a random orientation and unwinds its tilt as it spins, landing exactly on the input cells. The
next step turns the constants into options.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import Body, Color, ColorPair, EffectCharacter, Gradient, Scene, Vec3, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
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
        """Move the text plane far behind the canvas and queue its approach."""
        super().__init__(effect)
        self.final_colors: dict[EffectCharacter, ColorPair] = {}
        self.world = self.terminal.world
        self.build()

    def build(self) -> None:
        """Shade every visible character, move the text plane back, tip it, and queue the settle and approach."""
        world = self.world
        world.camera.set_perspective(1)
        world.set_light("front")
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
            # The light on its spot picks the frame: shadow when the text faces away, the final color facing
            # the light.
            scene = character.animation.new_scene(sync=Scene.SyncMetric.LIGHT)
            scene.apply_gradient_to_symbols(
                character.input_symbol, 1, fg_gradient=Gradient(SHADOW_COLOR, final_color, steps=10)
            )
            character.animation.activate_scene(scene)
            self.terminal.set_character_visibility(character, is_visible=True)
            self.active_characters.add(character)
        self.sheet = world.text_plane
        self.sheet.hide_facing_away = HIDE_BACK
        self.sheet.position = Vec3(0, 0, -START_DISTANCE)
        self.sheet.random_pose()
        self.sheet.settle("y", turns=2, frames=SPIN_FRAMES, ease=easing.out_cubic)
        approach = self.sheet.motion.new_path(speed=START_DISTANCE / SPIN_FRAMES, ease=easing.out_cubic)
        approach.new_waypoint(Vec3(0, 0, 0))
        self.sheet.motion.activate_path(approach)
        self.sheet.on_complete(self.finish)

    def finish(self, sheet: Body) -> None:
        """Put the text plane back at rest and show the characters in their final colors."""
        sheet.reset()
        for character, colors in self.final_colors.items():
            character.animation.deactivate_scene()
            character.animation.set_appearance(character.input_symbol, colors)

    def __next__(self) -> str:
        """Move the text plane one frame; the characters on it move with it."""
        if self.world.animating or self.active_characters:
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
