"""Aldous-Broder spanning tree generator.

This module provides the `AldousBroder` spanning tree generator.

The algorithm performs a random walk over the terminal character graph,
linking each newly encountered character to the current tree. The walk
continues until every reachable terminal character has been linked.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from terminaltexteffects.utils.spanningtree.base_generator import SpanningTreeGenerator

if TYPE_CHECKING:
    from terminaltexteffects.engine.base_character import EffectCharacter
    from terminaltexteffects.engine.terminal import Terminal


class AldousBroder(SpanningTreeGenerator):
    """Aldous-Broder spanning tree generator.

    The generator starts from a provided character or from a random
    character resolved from a random canvas coordinate. It then performs a
    random walk across neighboring characters, linking only characters that
    have not yet been linked into the tree.

    Attributes:
        char_last_linked (EffectCharacter | None): Character most recently linked into the tree.
            During initialization this is the starting character. On later steps it is `None`
            when the random walk moves to an already-linked character.
        char_link_order (list[EffectCharacter]): Characters in the order they were linked into
            the tree, beginning with the starting character.
        linked_char_last_visited (EffectCharacter | None): Character most recently visited
            without creating a new link. During initialization this is the starting character.
            On later steps it is set only when the random walk moves to a character that already
            has at least one link.
        complete (bool): Whether the algorithm is complete.

    """

    def __init__(self, terminal: Terminal, starting_char: EffectCharacter | None = None) -> None:
        """Initialize the algorithm.

        Args:
            terminal (Terminal): TTE Terminal.
            starting_char (EffectCharacter | None, optional): Starting character for the random
                walk. When `None`, a character is selected by resolving a random canvas
                coordinate to a terminal character.

        Raises:
            ValueError: No starting character could be resolved.

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
        """Advance the random walk by one neighboring character.

        If the chosen neighbor is not yet linked, it is linked to the current
        character and recorded in `char_link_order`. Otherwise,
        `linked_char_last_visited` records the already-linked character that
        was visited.

        Note:
            If all characters have already been linked, this method sets
            `complete` to `True` and returns immediately without advancing
            the walk.

        """
        self.linked_char_last_visited = self.char_last_linked = None
        if not self._unlinked_chars:
            self.complete = True
            return
        next_char = random.choice([n for n in self._current_char.neighbors.values() if n])
        if not next_char.links:
            self._current_char._link(next_char)
            self._unlinked_chars.remove(next_char)
            self.char_last_linked = next_char
            self.char_link_order.append(next_char)
        else:
            self.linked_char_last_visited = next_char
        self._current_char = next_char
