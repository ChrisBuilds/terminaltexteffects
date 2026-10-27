"""Die: a die rolls in from the left and comes to rest showing a five.

An Effect Guide recipe. Each face of the cube gets its own `Textured` look, a pattern of pips.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import Color, Gradient, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.drawing import Textured
from terminaltexteffects.engine.shapes import Cube
from terminaltexteffects.engine.tweens import rotation_about
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.geometry3d import Vec3

SIZE = 20
"""The die's width in columns. A face is `SIZE` columns wide and `SIZE // 2` rows tall."""


def pips(*spots: tuple[int, int]) -> str:
    """Return a face's text: a solid fill, with a blank pip at each (row, column) spot of a 3 by 3 grid."""
    rows = [["█"] * SIZE for _ in range(SIZE // 2)]
    for row, column in spots:
        # Each pip is two cells wide, which looks round on cells about twice as tall as they are wide.
        rows[2 + 3 * row][3 + 6 * column : 5 + 6 * column] = [" ", " "]
    return "\n".join("".join(row) for row in rows)


# Opposite faces add up to seven.
FACES = {
    "front": pips((0, 0), (0, 2), (1, 1), (2, 0), (2, 2)),
    "right": pips((0, 0), (1, 1), (2, 2)),
    "back": pips((0, 0), (2, 2)),
    "left": pips((0, 0), (0, 2), (2, 0), (2, 2)),
    "top": pips((1, 1)),
    "bottom": pips((0, 0), (0, 2), (1, 0), (1, 2), (2, 0), (2, 2)),
}


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "die", Die, DieConfig


@dataclass
class DieConfig(BaseConfig):
    """Configuration for the Die effect."""

    parser_spec = argutils.ParserSpec(
        name="die",
        help="A die rolls in and comes to rest.",
        description="die | A die rolls in and comes to rest.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c die",
    )


class DieIterator(BaseEffectIterator[DieConfig]):
    """Produce the frames of the Die effect."""

    def __init__(self, effect: Die) -> None:
        """Draw the die with a pip pattern per face and roll it to the center."""
        super().__init__(effect)
        self.world = self.terminal.world
        ivory = Gradient(Color("#4a3f35"), Color("#fff4e0"), steps=10)
        looks = {face: Textured(text, gradient=ivory) for face, text in FACES.items()}
        die = self.world.body(Cube(SIZE), at=(-60, 0, 0)).draw(faces=looks)
        die.rotation = rotation_about("diagonal", 120)
        # Roll to the center while tumbling, then settle with the five facing the viewer and a slight tilt.
        # A path's speed is units per frame, so the roll takes 150 frames, as long as the spin.
        roll = die.motion.new_path(speed=60 / 150, ease=easing.out_cubic)
        roll.new_waypoint(Vec3(0, 0, 0))
        die.motion.activate_path(roll)
        die.spin("z", turns=-1.5, frames=150, ease=easing.out_cubic)
        die.turn_to(rotation_about("x", 20) * rotation_about("y", -25), frames=60, ease=easing.out_back)
        die.hold(60)
        self.text_shown = False

    def __next__(self) -> str:
        """Roll the die, then swap it for the text."""
        if not self.world.animating:
            if self.text_shown:
                raise StopIteration
            for body in self.world.bodies:
                body.erase()  # The world hides its cells when it next paints.
            for character in self.terminal.get_characters():
                self.terminal.set_character_visibility(character, is_visible=True)
            self.text_shown = True
        self.update()
        return self.frame


class Die(BaseEffect[DieConfig]):
    """A die rolls in and comes to rest."""

    @property
    def _config_cls(self) -> type[DieConfig]:
        return DieConfig

    @property
    def _iterator_cls(self) -> type[DieIterator]:
        return DieIterator
