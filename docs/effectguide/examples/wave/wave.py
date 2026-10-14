"""Wave: a band of color sweeps across the text in a loop, for a set number of cycles or forever.

An Effect Guide example for the Looping and infinite effects pattern.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import Color, ColorPair, Gradient
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils

WAVE = Gradient(Color("#2040ff"), Color("#20e0ff"), Color("#ffffff"), steps=10, loop=True)
TICKS_PER_COLOR = 2
FINAL_COLOR = ColorPair(fg=Color("#20e0ff"))


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "wave", Wave, WaveConfig


@dataclass
class WaveConfig(BaseConfig):
    """Configuration for the Wave effect."""

    parser_spec = argutils.ParserSpec(
        name="wave",
        help="A band of color sweeps across the text in a loop.",
        description="wave | A band of color sweeps across the text in a loop.",
        epilog="Example: tte wave --cycles 0",
    )
    cycles: int = argutils.ArgSpec(
        name="--cycles",
        type=argutils.NonNegativeInt.type_parser,
        default=2,
        metavar=argutils.NonNegativeInt.METAVAR,
        help="Number of times the wave crosses the text. 0 loops until interrupted.",
    )  # pyright: ignore[reportAssignmentType]
    "int : Number of times the wave crosses the text. 0 loops until interrupted."


class WaveIterator(BaseEffectIterator[WaveConfig]):
    """Produce the frames of the Wave effect."""

    def __init__(self, effect: Wave) -> None:
        """Give every character a looping scene, offset by its column so the colors travel."""
        super().__init__(effect)
        colors = WAVE.spectrum
        self.cycle_ticks = len(colors) * TICKS_PER_COLOR
        self.ticks = 0
        for character in self.terminal.get_characters():
            offset = character.input_coord.column % len(colors)
            scene = character.animation.new_scene(is_looping=True)
            for color in colors[offset:] + colors[:offset]:
                scene.add_frame(character.input_symbol, TICKS_PER_COLOR, colors=ColorPair(fg=color))
            character.animation.activate_scene(scene)
            self.terminal.set_character_visibility(character, is_visible=True)
            self.active_characters.add(character)

    def __next__(self) -> str:
        """Advance the wave; after the last cycle, settle every character and stop."""
        if not self.active_characters:
            raise StopIteration
        if self.config.cycles and self.ticks == self.config.cycles * self.cycle_ticks:
            for character in self.active_characters:
                character.animation.deactivate_scene()
                character.animation.set_appearance(character.input_symbol, FINAL_COLOR)
            self.active_characters.clear()
            return self.frame
        self.ticks += 1
        self.update()
        return self.frame


class Wave(BaseEffect[WaveConfig]):
    """A band of color sweeps across the text in a loop."""

    @property
    def _config_cls(self) -> type[WaveConfig]:
        return WaveConfig

    @property
    def _iterator_cls(self) -> type[WaveIterator]:
        return WaveIterator
