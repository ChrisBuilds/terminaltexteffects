"""Roll: a cube whose turns follow its path, beside one that counts frames.

An Effect Guide example for the Rotation chapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import Color, ColorPair, EffectCharacter, Scene, Shaded, Vec3, easing, rotation_about
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.shapes import Cube
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.geometry import Coord

SIZE = 12
START, END = -24, 24
# A cube that rolls without slipping makes a quarter turn for every edge length it travels.
TURNS = (END - START) / (4 * SIZE)


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "roll", Roll, RollConfig


@dataclass
class RollConfig(BaseConfig):
    """Configuration for the Roll effect."""

    parser_spec = argutils.ParserSpec(
        name="roll",
        help="A cube whose turns follow its path, beside one that counts frames.",
        description="roll | A cube whose turns follow its path, beside one that counts frames.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c roll",
    )


class RollIterator(BaseEffectIterator[RollConfig]):
    """Produce the frames of the Roll effect."""

    def __init__(self, effect: Roll) -> None:
        """Send both cubes along the same eased path; only the top one's spin is synced to it."""
        super().__init__(effect)
        self.world = self.terminal.world
        self.labels: list[EffectCharacter] = []
        for y, synced in ((11, True), (-12, False)):
            cube = self.world.body(Cube(SIZE), at=(START, y, 0)).draw(Shaded())
            cube.rotation = rotation_about("y", 25)  # Turned a little so a side face shows as it rolls.
            path = cube.motion.new_path(speed=0.5, ease=easing.in_out_sine)
            path.new_waypoint(Vec3(END, y, 0))
            cube.motion.activate_path(path)
            if synced:
                # The spin's progress is the distance traveled, so it speeds up and slows down with the path.
                cube.spin("z", turns=-TURNS, local=True, sync=Scene.SyncMetric.DISTANCE)
            else:
                # The same turns over the same number of frames, at their own pace: the cube slides.
                cube.spin("z", turns=-TURNS, frames=path.max_steps, local=True)
            cube.hold(45)
        self.label("sync=DISTANCE", 11)
        self.label("frames", -11)
        self.text_shown = False

    def label(self, text: str, y: int) -> None:
        """Write `text` at the left edge, `y` rows above the canvas center."""
        row = self.terminal.canvas.center.row + y
        for offset, symbol in enumerate(text):
            character = self.terminal.add_character(symbol, Coord(self.terminal.canvas.left + 1 + offset, row))
            character.animation.set_appearance(symbol, ColorPair(fg=Color("#a0a0a0")))
            self.terminal.set_character_visibility(character, is_visible=True)
            self.labels.append(character)

    def __next__(self) -> str:
        """Roll the cubes, then swap them for the text."""
        if not self.world.animating:
            if self.text_shown:
                raise StopIteration
            for body in self.world.bodies:
                body.erase()  # The world hides its cells when it next paints.
            for character in self.labels:
                self.terminal.set_character_visibility(character, is_visible=False)
            for character in self.terminal.get_characters():
                self.terminal.set_character_visibility(character, is_visible=True)
            self.text_shown = True
        self.update()
        return self.frame


class Roll(BaseEffect[RollConfig]):
    """A cube whose turns follow its path, beside one that counts frames."""

    @property
    def _config_cls(self) -> type[RollConfig]:
        return RollConfig

    @property
    def _iterator_cls(self) -> type[RollIterator]:
        return RollIterator
