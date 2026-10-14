"""Gather: scattered dots gather into the text one group at a time, then the text flashes.

An Effect Guide example for the Phases and staggered starts pattern.
"""

from __future__ import annotations

from dataclasses import dataclass

from terminaltexteffects import CharacterOrder, Color, ColorPair, EffectCharacter, Gradient, Scene, easing
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils

DOT_COLOR = Color("#606060")
TEXT_COLOR = Color("#40c0ff")
ARRIVE = Gradient(DOT_COLOR, TEXT_COLOR, steps=8)
FLASH = Gradient(Color("#ffffff"), TEXT_COLOR, steps=10)
SCATTER_TICKS = 30
TICKS_BETWEEN_GROUPS = 4


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "gather", Gather, GatherConfig


@dataclass
class GatherConfig(BaseConfig):
    """Configuration for the Gather effect."""

    parser_spec = argutils.ParserSpec(
        name="gather",
        help="Scattered dots gather into the text one group at a time, then the text flashes.",
        description="gather | Scattered dots gather into the text one group at a time, then the text flashes.",
        epilog="Example: tte gather --gather-order column_left_to_right",
    )
    gather_order: CharacterOrder = argutils.ArgSpec(
        name="--gather-order",
        type=argutils.CharacterOrderArg.type_parser,
        default=CharacterOrder.ROW_TOP_TO_BOTTOM,
        metavar=" ".join(argutils.CharacterOrderArg.METAVAR),
        help="Order in which groups of characters gather.",
    )  # pyright: ignore[reportAssignmentType]
    "CharacterOrder : Order in which groups of characters gather."


class GatherIterator(BaseEffectIterator[GatherConfig]):
    """Produce the frames of the Gather effect, one phase after another."""

    def __init__(self, effect: Gather) -> None:
        """Scatter the characters as dots and queue the groups that gather."""
        super().__init__(effect)
        self.phase = "scatter"
        self.ticks_in_phase = 0
        self.pending_groups = self.terminal.get_characters_grouped(order=self.config.gather_order)
        self.pending_groups.reverse()  # So pop() takes the first group.
        for character in self.terminal.get_characters():
            character.motion.set_coordinate(self.terminal.canvas.random_coord())
            character.animation.set_appearance(".", ColorPair(fg=DOT_COLOR))
            self.terminal.set_character_visibility(character, is_visible=True)

    def start_gathering(self, character: EffectCharacter) -> None:
        """Send a character home, turning from a dot into its symbol on the way."""
        path = character.motion.new_path(speed=0.8, ease=easing.in_out_sine)
        path.new_waypoint(character.input_coord)
        character.motion.activate_path(path)
        scene = character.animation.new_scene(sync=Scene.SyncMetric.DISTANCE)
        scene.apply_gradient_to_symbols((".", "o", character.input_symbol), 1, fg_gradient=ARRIVE)
        character.animation.activate_scene(scene)
        self.active_characters.add(character)

    def __next__(self) -> str:
        """Run the current phase for one tick and return the frame."""
        self.ticks_in_phase += 1
        if self.phase == "scatter":
            if self.ticks_in_phase == SCATTER_TICKS:
                self.phase, self.ticks_in_phase = "gather", 0
        elif self.phase == "gather":
            if self.pending_groups and self.ticks_in_phase % TICKS_BETWEEN_GROUPS == 1:
                for character in self.pending_groups.pop():
                    self.start_gathering(character)
            if not self.pending_groups and not self.active_characters:
                self.start_flash()
        elif self.phase == "flash" and not self.active_characters:
            raise StopIteration
        self.update()
        return self.frame

    def start_flash(self) -> None:
        """Flash every character from white to the text color."""
        self.phase, self.ticks_in_phase = "flash", 0
        for character in self.terminal.get_characters():
            scene = character.animation.new_scene()
            scene.apply_gradient_to_symbols(character.input_symbol, 3, fg_gradient=FLASH)
            character.animation.activate_scene(scene)
            self.active_characters.add(character)


class Gather(BaseEffect[GatherConfig]):
    """Scattered dots gather into the text one group at a time, then the text flashes."""

    @property
    def _config_cls(self) -> type[GatherConfig]:
        return GatherConfig

    @property
    def _iterator_cls(self) -> type[GatherIterator]:
        return GatherIterator
