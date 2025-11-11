"""Recursive Backtracker minimum spanning tree algorithm.

This module provides the `RecursiveBacktracker` spanning tree generator
implementation. The algorithm builds a spanning tree over a graph of
`EffectCharacter` nodes using the depth-first recursive backtracker
approach (implemented iteratively with an explicit stack).

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
    """Recursive Backtracker tree generator algorithm.

    Attributes:
        char_last_linked (EffectCharacter | None): Character linked into the tree on the
            last step. None, if no character was linked during the last step.
        char_link_order (list[EffectCharacter]): Characters in linked order.
        stack (list[EffectCharacter]): Characters on the stack.
        stack_last_popped (EffectCharacter | None): Character popped off the stack on the
            last step. None if no character was popped during the last step.

    """

    def __init__(self, terminal: Terminal, starting_char: EffectCharacter | None = None) -> None:
        """Initialize the algorithm.

        Args:
            terminal (Terminal): TTE Terminal.
            starting_char (EffectCharacter | None, optional): Starting EffectCharacter. Defaults to None.

        Attributes:
            char_last_linked (EffectCharacter | None): Last character linked into the tree.
            char_link_order (list[EffectCharacter]): Characters in linked order.
            stack (list[EffectCharacter]): Characters on the stack.
            stack_last_popped (EffectCharacter | None): Last character popped off the stack.
            complete (bool): Whether the algorithm is complete.

        Raises:
            ValueError: Unable to find a starting character.

        """
        super().__init__(terminal)
        starting_char = starting_char or terminal.get_character_by_input_coord(terminal.canvas.random_coord())
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
        """Progress the algorithm by one step."""
        self.char_last_linked = None
        self.stack_last_popped = None
        if self.stack:
            neighbors = [neighbor for neighbor in self._current_char.neighbors.values() if neighbor]
            unvisited_neighbors = [neighbor for neighbor in neighbors if not neighbor.links]
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
