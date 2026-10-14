"""Grow: the text grows along a spanning tree, then a pulse runs back along the tree's branches.

An Effect Guide example for the Spanning trees pattern.
"""

from __future__ import annotations

import typing
from dataclasses import dataclass

from terminaltexteffects import Color, ColorPair, EffectCharacter, Gradient
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.spanningtree.algo.aldousbroder import AldousBroder
from terminaltexteffects.utils.spanningtree.algo.breadthfirst import BreadthFirst
from terminaltexteffects.utils.spanningtree.algo.primssimple import PrimsSimple
from terminaltexteffects.utils.spanningtree.algo.recursivebacktracker import RecursiveBacktracker

ALGORITHMS = {
    "prims_simple": PrimsSimple,
    "recursive_backtracker": RecursiveBacktracker,
    "aldous_broder": AldousBroder,
}
GROWN_COLOR = ColorPair(fg=Color("#3a7a3a"))
PULSE = Gradient(Color("#ffffff"), Color("#80ff80"), steps=8)
LINKS_PER_TICK = 3


def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Return the command name, effect class, and configuration class TTE registers."""
    return "grow", Grow, GrowConfig


@dataclass
class GrowConfig(BaseConfig):
    """Configuration for the Grow effect."""

    parser_spec = argutils.ParserSpec(
        name="grow",
        help="The text grows along a spanning tree, then a pulse runs along the tree's branches.",
        description="grow | The text grows along a spanning tree, then a pulse runs along the tree's branches.",
        epilog="Example: tte grow --algorithm recursive_backtracker",
    )
    algorithm: typing.Literal["prims_simple", "recursive_backtracker", "aldous_broder"] = argutils.ArgSpec(
        name="--algorithm",
        default="prims_simple",
        choices=list(ALGORITHMS),
        help="Algorithm that builds the spanning tree.",
    )  # pyright: ignore[reportAssignmentType]
    "typing.Literal['prims_simple', 'recursive_backtracker', 'aldous_broder'] : Algorithm that builds the tree."


class GrowIterator(BaseEffectIterator[GrowConfig]):
    """Produce the frames of the Grow effect."""

    def __init__(self, effect: Grow) -> None:
        """Build the whole spanning tree up front, and prepare the pulse that follows it."""
        super().__init__(effect)
        tree = ALGORITHMS[self.config.algorithm](self.terminal, limit_to_text_boundary=True)
        while not tree.complete:
            tree.step()
        self.link_order = [character for character in tree.char_link_order if not character.is_fill_character]
        self.link_order.reverse()  # So pop() takes the first character linked.
        self.root = tree.char_link_order[0]
        self.pulse = BreadthFirst(self.terminal, self.root)
        for character in self.terminal.get_characters():
            character.animation.set_appearance(character.input_symbol, GROWN_COLOR)
            scene = character.animation.new_scene(scene_id="pulse")
            scene.apply_gradient_to_symbols(character.input_symbol, 2, fg_gradient=PULSE)

    def start_pulse(self, character: EffectCharacter) -> None:
        """Play the pulse scene on a character the pulse has just reached."""
        if not character.is_fill_character:
            character.animation.activate_scene("pulse")
            self.active_characters.add(character)

    def __next__(self) -> str:
        """Grow a few characters per tick; once all have grown, advance the pulse one layer per tick."""
        if self.link_order:
            for _ in range(LINKS_PER_TICK):
                if self.link_order:
                    self.terminal.set_character_visibility(self.link_order.pop(), is_visible=True)
        elif not self.pulse.complete:
            if not self.pulse.char_explore_order:  # The first pulse tick: start at the root.
                self.start_pulse(self.root)
            self.pulse.step()
            for character in self.pulse.explored_last_step:
                self.start_pulse(character)
        elif not self.active_characters:
            raise StopIteration
        self.update()
        return self.frame


class Grow(BaseEffect[GrowConfig]):
    """The text grows along a spanning tree, then a pulse runs along the tree's branches."""

    @property
    def _config_cls(self) -> type[GrowConfig]:
        return GrowConfig

    @property
    def _iterator_cls(self) -> type[GrowIterator]:
        return GrowIterator
