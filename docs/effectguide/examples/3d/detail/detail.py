"""Detail: the same sphere with more and more faces.

An Effect Guide example for the Performance chapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import Color, ColorPair, EffectCharacter, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.space3d import Shaded, Space3D, Sphere, Wireframe
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.geometry import Coord


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "detail", Detail, DetailConfig


@dataclass
class DetailConfig(BaseConfig):
    """Configuration for the Detail effect."""

    parser_spec = argutils.ParserSpec(
        name="detail",
        help="The same sphere with more and more faces.",
        description="detail | The same sphere with more and more faces.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c detail --wireframe",
    )
    wireframe: bool = argutils.ArgSpec(
        name="--wireframe",
        default=False,
        action="store_true",
        help="Draw only the edges of the spheres.",
    )  # pyright: ignore[reportAssignmentType]
    "bool : Draw only the edges of the spheres."


DETAIL = ((8, 4), (16, 8), (32, 16))
"""Each sphere's segments around and rings top to bottom. Each step doubles both, so four times the faces."""


class DetailIterator(BaseEffectIterator[DetailConfig]):
    """Produce the frames of the Detail effect."""

    def __init__(self, effect: Detail) -> None:
        """Draw the spheres side by side and turn them together."""
        super().__init__(effect)
        self.space = Space3D(self.terminal)
        self.labels: list[EffectCharacter] = []
        look = Wireframe() if self.config.wireframe else Shaded()
        for index, (segments, rings) in enumerate(DETAIL):
            x = (index - 1) * 26
            sphere = self.space.body(Sphere(radius=11, segments=segments, rings=rings), at=(x, 0, 0)).draw(look)
            sphere.rotate("x", 20)
            sphere.spin("y", turns=1, frames=360, ease=easing.in_out_sine)
            self.label(f"{segments} by {rings}", x)
        self.text_shown = False

    def label(self, text: str, x: int) -> None:
        """Write `text` on the bottom row, under the body at `x`. Labels are plain characters, not part of the space."""
        start = self.terminal.canvas.center.column + x - len(text) // 2
        for offset, symbol in enumerate(text):
            character = self.terminal.add_character(symbol, Coord(start + offset, self.terminal.canvas.bottom))
            character.animation.set_appearance(symbol, ColorPair(fg=Color("#a0a0a0")))
            self.terminal.set_character_visibility(character, is_visible=True)
            self.labels.append(character)

    def __next__(self) -> str:
        """Turn the spheres, then swap them for the text."""
        if self.space.animating:
            self.space.step()
        elif not self.text_shown:
            for body in self.space.bodies:
                body.erase()
            for character in self.labels:
                self.terminal.set_character_visibility(character, is_visible=False)
            self.space.step()  # Hides the surface characters once nothing is drawn.
            for character in self.terminal.get_characters():
                self.terminal.set_character_visibility(character, is_visible=True)
            self.text_shown = True
        else:
            raise StopIteration
        self.update()
        return self.frame


class Detail(BaseEffect[DetailConfig]):
    """The same sphere with more and more faces."""

    @property
    def _config_cls(self) -> type[DetailConfig]:
        return DetailConfig

    @property
    def _iterator_cls(self) -> type[DetailIterator]:
        return DetailIterator
