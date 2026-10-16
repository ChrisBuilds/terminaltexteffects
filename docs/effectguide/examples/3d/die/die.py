"""Die: a die rolls in from the left and comes to rest showing a five.

An Effect Guide recipe. Each face of the cube gets its own `Textured` look, a pattern of pips.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import Color, Gradient, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.space3d import Cube, Space3D, Textured, rotation_about
from terminaltexteffects.utils import argutils

SIZE = 20
"""The die's width in columns. A face is `SIZE` columns wide and `SIZE // 2` rows tall."""


def pips(*spots: tuple[int, int]) -> str:
    """Return a face's text: a solid fill, with a blank pip at each (row, column) spot of a 3 by 3 grid."""
    rows = [["█"] * SIZE for _ in range(SIZE // 2)]
    for row, column in spots:
        # Each pip is two cells wide, which looks round on cells about twice as tall as they are wide.
        rows[2 + 3 * row][3 + 6 * column : 5 + 6 * column] = [" ", " "]
    return "\n".join("".join(row) for row in rows)


# Box faces are tagged 0 front, 1 right, 2 back, 3 left, 4 top and 5 bottom. Opposite faces add up to seven.
FACES = {
    0: pips((0, 0), (0, 2), (1, 1), (2, 0), (2, 2)),
    1: pips((0, 0), (1, 1), (2, 2)),
    2: pips((0, 0), (2, 2)),
    3: pips((0, 0), (0, 2), (2, 0), (2, 2)),
    4: pips((1, 1)),
    5: pips((0, 0), (0, 2), (1, 0), (1, 2), (2, 0), (2, 2)),
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
        self.space = Space3D(self.terminal)
        ivory = Gradient(Color("#4a3f35"), Color("#fff4e0"), steps=10)
        looks = {tag: Textured(text, gradient=ivory) for tag, text in FACES.items()}
        die = self.space.body(Cube(SIZE), at=(-60, 0, 0)).draw(faces=looks)
        die.set_rotation(rotation_about("diagonal", 120))
        # Roll to the center while tumbling, then settle with the five facing the viewer and a slight tilt.
        die.move_to(0, 0, 0, frames=150, ease=easing.out_cubic)
        die.spin("z", turns=-1.5, frames=150, ease=easing.out_cubic, together=True)
        die.turn_to(rotation_about("x", 20) * rotation_about("y", -25), frames=60, ease=easing.out_back)
        die.hold(60)
        self.text_shown = False

    def __next__(self) -> str:
        """Roll the die, then swap it for the text."""
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


class Die(BaseEffect[DieConfig]):
    """A die rolls in and comes to rest."""

    @property
    def _config_cls(self) -> type[DieConfig]:
        return DieConfig

    @property
    def _iterator_cls(self) -> type[DieIterator]:
        return DieIterator
