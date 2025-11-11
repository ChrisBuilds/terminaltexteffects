"""Aldous Broder minimum spanning tree algorithm.

This module provides the `AldousBroder` spanning tree generator
implementation.

The algorithm performs a random walk over the graph, linking unvisited
nodes as they are encountered. The process continues until all nodes
have been linked into the spanning tree.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from terminaltexteffects.utils.spanningtree.base_generator import SpanningTreeGenerator

if TYPE_CHECKING:
    from terminaltexteffects.engine.base_character import EffectCharacter
    from terminaltexteffects.engine.terminal import Terminal


class AldousBroder(SpanningTreeGenerator):
    """Aldous Broder minimum spanning tree algorithm.

    Attributes:
        char_last_linked (EffectCharacter | None): Character linked into the tree on the
            last step. None, if no character was linked during the last step.
        char_link_order (list[EffectCharacter]): Characters in linked order.
        linked_char_last_visited (EffectCharacter | None): Last linked character visited. This
            is a linked character that was visited during the random walk but not linked,
            because it was already part of the spanning tree. None, if no linked character was
            visited during the last step.
        complete (bool): Whether the algorithm is complete.

    """

    def __init__(self, terminal: Terminal, starting_char: EffectCharacter | None = None) -> None:
        """Initialize the algorithm.

        Args:
            terminal (Terminal): TTE Terminal.
            starting_char (EffectCharacter | None, optional): Starting EffectCharacter. Defaults to None.

        """
        super().__init__(terminal)
        starting_char = starting_char or terminal.get_character_by_input_coord(terminal.canvas.random_coord())
        if starting_char is None:
            msg = "Unable to find a starting character."
            raise ValueError(msg)
        self._unlinked_chars = set(self.terminal.get_characters(inner_fill_chars=True, outer_fill_chars=True))
        self._unlinked_chars.remove(starting_char)
        self._current_char = starting_char
        self.char_last_linked: EffectCharacter | None = self._current_char
        self.char_link_order: list[EffectCharacter] = [self._current_char]
        self.linked_char_last_visited: EffectCharacter | None = self._current_char
        self.complete = False

    def step(self) -> None:
        """Perform a single step of the algorithm."""
        self.linked_char_last_visited = self.char_last_linked = None
        if not self._unlinked_chars:
            self.complete = True
        next_char = random.choice([n for n in self._current_char.neighbors.values() if n])
        if not next_char.links:
            self._current_char._link(next_char)
            self._unlinked_chars.remove(next_char)
            self.char_last_linked = next_char
            self.char_link_order.append(next_char)
        else:
            self.linked_char_last_visited = next_char
        self._current_char = next_char
