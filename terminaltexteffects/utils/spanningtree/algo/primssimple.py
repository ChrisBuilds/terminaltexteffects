"""Simplified Prim-style spanning tree generator.

A simplified Prim-style algorithm uses equal weight for all links and
selects from the current edge set at random.

The algorithm starts from a chosen starting character (or a random one
from the terminal) and grows by randomly linking to an unlinked neighbor.

When a neighbor is linked, the neighbor is checked for unlinked neighbors. If
it has unlinked neighbors, it is considered an edge. On each step, a random edge
is chosen and the process repeats.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from terminaltexteffects.utils.spanningtree.base_generator import SpanningTreeGenerator

if TYPE_CHECKING:
    from terminaltexteffects.engine.base_character import EffectCharacter
    from terminaltexteffects.engine.terminal import Terminal


class PrimsSimple(SpanningTreeGenerator):
    """Simplified Prim-style spanning tree generator.

    Attributes:
        char_last_linked (EffectCharacter | None): Character most recently linked into the tree.
            During initialization this is the starting character. On later steps it retains
            its previous value if no new character is linked.
        char_link_order (list[EffectCharacter]): Characters in the order they were linked into
            the tree, beginning with the starting character.
        edge_chars (list[EffectCharacter]): Characters currently considered edge candidates.
            During initialization this contains the starting character.
        edge_last_added (EffectCharacter | None): Character most recently added to the edge list.
            During initialization this is the starting character. On later steps it retains its
            previous value if no new edge character is added.
        edge_last_popped (EffectCharacter | None): Character popped off the edge list on the
            last step. None if no character was popped during the last step.
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
            starting_char (EffectCharacter | None, optional): Starting character for the tree
                generation. When `None`, a character is selected by resolving a random canvas
                coordinate to a terminal character.
            limit_to_text_boundary (bool, optional): If True, the graph will not link to neighbors outside the text
                boundary.

        Raises:
            ValueError: Unable to find a starting character.

        """
        super().__init__(terminal)
        starting_char = starting_char or terminal.get_character_by_input_coord(
            terminal.canvas.random_coord(within_text_boundary=limit_to_text_boundary),
        )
        if starting_char is None:
            msg = "Unable to find a starting character."
            raise ValueError(msg)
        self.limit_to_text_boundary = limit_to_text_boundary
        self._current_char = starting_char
        self.char_last_linked: EffectCharacter | None = self._current_char
        self.char_link_order: list[EffectCharacter] = [self._current_char]
        self.edge_chars = [self._current_char]
        self.edge_last_added: EffectCharacter | None = self._current_char
        self.edge_last_popped: EffectCharacter | None = None
        self.complete = False

    def step(self) -> None:
        """Advance the tree generation by one step.

        Each step pops one character from the current edge list. If that
        character has any eligible unlinked neighbors, one is linked into the
        tree, the popped character may be returned to the edge list if it still
        has eligible neighbors, and the newly linked character may be added to
        the edge list as well.

        Note:
            `complete` becomes `True` only when `edge_chars` is already empty at
            the start of a call. If a step pops the last edge character and
            links nothing, the generator ends that call with an empty edge list
            and `complete` still set to `False`.

        """
        if self.edge_chars:
            self._current_char = self.edge_chars.pop(random.randrange(len(self.edge_chars)))
            self.edge_last_popped = self._current_char
            unlinked_neighbors = self.get_neighbors(
                self._current_char,
                limit_to_text_boundary=self.limit_to_text_boundary,
            )

            if unlinked_neighbors:
                next_char = unlinked_neighbors.pop(random.randrange(len(unlinked_neighbors)))
                self._current_char._link(next_char)
                self.char_link_order.append(next_char)
                self.char_last_linked = next_char
                if unlinked_neighbors:
                    self.edge_chars.append(self._current_char)
                unlinked_neighbors = self.get_neighbors(
                    next_char,
                    limit_to_text_boundary=self.limit_to_text_boundary,
                )
                if unlinked_neighbors:
                    self.edge_chars.append(next_char)
                    self.edge_last_added = next_char
        else:
            self.complete = True
