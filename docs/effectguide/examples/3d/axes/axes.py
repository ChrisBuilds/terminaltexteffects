"""Axes: the world axes and the text plane turn together, so you can see where things sit in 3D.

An Effect Guide example for the Space and Coordinates chapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import Body, Color, ColorPair, EffectCharacter, easing, rotation_about
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "axes", Axes, AxesConfig


@dataclass
class AxesConfig(BaseConfig):
    """Configuration for the Axes effect."""

    parser_spec = argutils.ParserSpec(
        name="axes",
        help="The world axes and the text plane turn together.",
        description="axes | The world axes and the text plane turn together.",
        epilog="Example: tte --canvas-width 80 --canvas-height 24 --anchor-text c axes",
    )


class AxesIterator(BaseEffectIterator[AxesConfig]):
    """Produce the frames of the Axes effect."""

    def __init__(self, effect: Axes) -> None:
        """Attach the axes to bodies, show the text on the text plane, and queue the turns."""
        super().__init__(effect)
        self.world = self.terminal.world
        self.markers: list[EffectCharacter] = []
        # Each axis is a line of dots through the origin, with its label just past the positive end.
        x_axis = self.axis((1, 0, 0), 28, "#ff5f5f", "X")
        y_axis = self.axis((0, 1, 0), 18, "#5fff87", "Y")
        z_axis = self.axis((0, 0, 1), 28, "#5fafff", "Z")
        # The input characters sit on the text plane, each on its input cell, and turn with it.
        self.text = self.world.text_plane
        for character in self.terminal.get_characters():
            if character.input_symbol != " ":
                self.terminal.set_character_visibility(character, is_visible=True)
                self.active_characters.add(character)

        view = rotation_about("x", 25) * rotation_about("y", -35)
        for body in (x_axis, y_axis, z_axis, self.text):
            body.hold(30).turn_to(view, frames=90, ease=easing.in_out_cubic)
            body.spin("y", turns=1, frames=240, ease=easing.in_out_sine)
            body.turn_to_rest(frames=90, ease=easing.in_out_cubic).hold(30)
        self.axes_shown = True

    def axis(self, direction: tuple[int, int, int], length: int, color: str, label: str) -> Body:
        """Return a body holding a dotted axis along `direction`, `length` columns each way, and its label."""
        # A body with no shape is a plain frame of reference: its children turn with it.
        body = self.world.body()
        x, y, z = direction
        for step in range(-length, length + 3, 2):
            symbol = label if step > length else "•"
            dot = self.terminal.add_character(symbol, self.terminal.canvas.center)
            dot.animation.set_appearance(symbol, ColorPair(fg=Color(color)))
            dot.layer = -1  # A lower layer than the text, so the text wins cells it shares with an axis.
            dot.attach(body, at=(step * x, step * y, step * z))
            self.terminal.set_character_visibility(dot, is_visible=True)
            self.active_characters.add(dot)
            self.markers.append(dot)
        return body

    def __next__(self) -> str:
        """Turn everything, then hide the axes and leave the text."""
        if self.world.animating:
            self.update()
            return self.frame
        if self.axes_shown:
            for marker in self.markers:
                self.terminal.set_character_visibility(marker, is_visible=False)
            self.axes_shown = False
            self.update()
            return self.frame
        raise StopIteration


class Axes(BaseEffect[AxesConfig]):
    """The world axes and the text plane turn together."""

    @property
    def _config_cls(self) -> type[AxesConfig]:
        return AxesConfig

    @property
    def _iterator_cls(self) -> type[AxesIterator]:
        return AxesIterator
