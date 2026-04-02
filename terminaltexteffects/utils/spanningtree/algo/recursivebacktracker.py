"""Recursive backtracker spanning tree generator.

This module provides the `RecursiveBacktracker` spanning tree
generator. The algorithm builds a spanning tree over a graph of
`EffectCharacter` nodes using a depth-first recursive backtracker
approach implemented iteratively with an explicit stack.

The algorithm starts from a chosen starting character (or a random one
from the terminal) and grows the tree by repeatedly linking to a
randomly selected unvisited neighbor. Linked cells are added to
the stack.

When a node has no unvisited neighbors the algorithm backtracks by
popping the stack until it finds a node with unvisited neighbors.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from terminaltexteffects.utils.spanningtree.base_generator import SpanningTreeGenerator

if TYPE_CHECKING:
    from terminaltexteffects.engine.base_character import EffectCharacter
    from terminaltexteffects.engine.terminal import Terminal


class RecursiveBacktracker(SpanningTreeGenerator):
    """Recursive backtracker spanning tree generator.

    Attributes:
        char_last_linked (EffectCharacter | None): Character most recently linked into the tree.
            During initialization this is the starting character. On later steps it is `None`
            when the generator backtracks instead of linking a new character.
        char_link_order (list[EffectCharacter]): Characters in the order they were linked into
            the tree, beginning with the starting character.
        stack (list[EffectCharacter]): Depth-first traversal stack. During initialization it
            contains the starting character.
        stack_last_popped (EffectCharacter | None): Character popped off the stack on the
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
        self.limit_to_text_boundary = limit_to_text_boundary
        starting_char = starting_char or terminal.get_character_by_input_coord(
            terminal.canvas.random_coord(within_text_boundary=limit_to_text_boundary),
        )
        if starting_char is None:
            msg = "Unable to find a starting character."
            raise ValueError(msg)
        self._current_char = starting_char
        self.char_last_linked: EffectCharacter | None = self._current_char
        self.char_link_order: list[EffectCharacter] = [self._current_char]
        self.stack: list[EffectCharacter] = [self._current_char]
        self.stack_last_popped: EffectCharacter | None = None
        self.complete = False

    def step(self) -> None:
        """Advance the traversal by one step.

        Each step either links one unvisited neighbor and descends deeper
        into the tree, or pops the traversal stack to backtrack when the
        current character has no unvisited neighbors.

        Note:
            `complete` becomes `True` only on a subsequent call after
            the stack is already empty. If the last stack item is popped
            during this call, the generator ends the step with an empty
            stack and `complete` still set to `False`.

        """
        self.char_last_linked = None
        self.stack_last_popped = None
        if self.stack:
            unvisited_neighbors = self.get_neighbors(
                self._current_char,
                limit_to_text_boundary=self.limit_to_text_boundary,
            )
            if unvisited_neighbors:
                next_char = random.choice(unvisited_neighbors)
                self._current_char._link(next_char)
                self.char_link_order.append(next_char)
                self.char_last_linked = next_char
                self.stack.append(next_char)
                self._current_char = next_char
            else:
                self.stack_last_popped = self.stack.pop()
                if self.stack:
                    self._current_char = self.stack[-1]
        else:
            self.complete = True
