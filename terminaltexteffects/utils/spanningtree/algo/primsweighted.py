"""Prims weighted minimum spanning tree algorithm implementation.

This module provides the `PrimsWeighted` spanning tree generator
implementation. The algorithm builds a spanning tree over a graph of
`EffectCharacter` nodes using Prim's algorithm with weighted edges.

The algorithm starts from a chosen starting character (or a random one
from the terminal) and grows the tree by linking to the unlinked neighbor
with the lowest weight.

When a neighbor is linked, its unlinked neighbors are added to the pool of
potential links. On each step, the unlinked neighbor with the lowest weight
is chosen and the process repeats.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from terminaltexteffects.utils.spanningtree.base_generator import SpanningTreeGenerator

if TYPE_CHECKING:
    from terminaltexteffects.engine.base_character import EffectCharacter
    from terminaltexteffects.engine.terminal import Terminal


@dataclass
class WeightedLink:
    """Weighted link.

    Attributes:
        char_a (EffectCharacter): One end of the link.
        char_b (EffectCharacter): The other end of the link.
        weight (int): Weight of the link.

    """

    char_a: EffectCharacter
    char_b: EffectCharacter
    weight: int


class PrimsWeighted(SpanningTreeGenerator):
    """Prims weighted minimum spanning tree algorithm.

    Attributes:
        char_last_linked (EffectCharacter | None): Character linked into the tree on the
            last step. None, if no character was linked during the last step.
        char_link_order (list[EffectCharacter]): Characters in linked order.
        neighbors_last_added (list[EffectCharacter]): Characters added as neighbors on the
            last step.
        complete (bool): Whether the algorithm is complete.

    """

    def __init__(
        self,
        terminal: Terminal,
        starting_char: EffectCharacter | None = None,
        *,
        limit_to_text_boundary: bool = False,
    ) -> None:
        """Initialize the algorithm.

        Args:
            terminal (Terminal): TTE Terminal.
            starting_char (EffectCharacter | None, optional): Starting EffectCharacter. Defaults to None.
            limit_to_text_boundary (bool, optional): If True, the graph will not link to neighbors outside the text
                boundary.

        """
        super().__init__(terminal)
        starting_char = starting_char or terminal.get_character_by_input_coord(terminal.canvas.random_coord())
        self.limit_to_text_boundary = limit_to_text_boundary
        if starting_char is None:
            msg = "Unable to find a starting character."
            raise ValueError(msg)
        self._char_weights: dict[EffectCharacter, int] = {}
        for char in self.terminal.get_characters(inner_fill_chars=True, outer_fill_chars=True):
            self._char_weights[char] = random.randint(0, 99)
        self._current_char = starting_char
        self.char_last_linked: EffectCharacter | None = self._current_char
        self.char_link_order: list[EffectCharacter] = [self._current_char]
        self.neighbors_last_added: list[EffectCharacter] = []
        self.complete = False
        self._pending_weighted_links: dict[int, list[WeightedLink]] = defaultdict(list)
        self.add_weighted_links(self._current_char)

    def add_weighted_links(self, char: EffectCharacter) -> None:
        """Add weighted links for the given character's unlinked neighbors.

        Args:
            char (EffectCharacter): Character for which weighted links are added.

        """
        self.neighbors_last_added.clear()
        for neighbor in self.get_neighbors(char, limit_to_text_boundary=self.limit_to_text_boundary):
            self.neighbors_last_added.append(neighbor)
            self._pending_weighted_links[self._char_weights[neighbor]].append(
                WeightedLink(char, neighbor, self._char_weights[neighbor]),
            )

    def get_lowest_weight_link(self) -> WeightedLink | None:
        """Get the weighted link with the lowest weight.

        Returns:
            WeightedLink | None: The weighted link with the lowest weight, or None if no links are available.

        """
        while self._pending_weighted_links:
            lowest_weight = min(self._pending_weighted_links)
            links_at_weight = self._pending_weighted_links[lowest_weight]
            link = links_at_weight.pop(random.randrange(len(links_at_weight)))
            if not links_at_weight:
                self._pending_weighted_links.pop(lowest_weight)
            if not link.char_b.links:
                return link
        return None

    def step(self) -> None:
        """Perform a single step of the algorithm."""
        if self._pending_weighted_links:
            next_link = self.get_lowest_weight_link()
            if next_link is None:
                self.complete = True
                return
            next_link.char_a._link(next_link.char_b)
            self.char_last_linked = next_link.char_b
            self.char_link_order.append(next_link.char_b)
            self.add_weighted_links(next_link.char_b)
        else:
            self.complete = True
            self.char_last_linked = None
            self.neighbors_last_added.clear()
            return
