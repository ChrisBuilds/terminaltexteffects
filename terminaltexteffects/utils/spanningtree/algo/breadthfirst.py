"""Breadth-first traversal over an already linked character graph.

This module provides the `BreadthFirst` traversal helper. It performs a
breadth-first walk over existing `EffectCharacter.links` relationships
instead of generating a new spanning tree.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from terminaltexteffects.utils.spanningtree.base_generator import SpanningTreeGenerator

if TYPE_CHECKING:
    from terminaltexteffects.engine.base_character import EffectCharacter
    from terminaltexteffects.engine.terminal import Terminal


class BreadthFirst(SpanningTreeGenerator):
    """Breadth-first traversal helper.

    Uses breadth-first traversal to explore an already linked graph of
    `EffectCharacter` nodes.

    Attributes:
        starting_char (EffectCharacter): Character where the traversal begins.
        explored_last_step (list[EffectCharacter]): Characters newly discovered during the
            most recent step.
        char_explore_order (list[EffectCharacter]): Characters in the order they were first
            discovered by the traversal.
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
            starting_char (EffectCharacter | None, optional): Starting character for the
                traversal. When `None`, a character is selected by resolving a random canvas
                coordinate to a terminal character.
            limit_to_text_boundary (bool, optional): If True, the starting character, if not provided, will
                be chosen within the text boundary. This should be True if the spanning tree was generated
                with limit_to_text_boundary=True.

        Raises:
            ValueError: Unable to find a starting character.

        """
        super().__init__(terminal)
        self._limit_to_text_boundary = limit_to_text_boundary
        self.starting_char = starting_char or terminal.get_character_by_input_coord(
            terminal.canvas.random_coord(within_text_boundary=limit_to_text_boundary),
        )
        if self.starting_char is None:
            msg = "Unable to find a starting character."
            raise ValueError(msg)
        self._frontier = [self.starting_char]
        self._explored: dict[EffectCharacter, EffectCharacter] = {self.starting_char: self.starting_char}
        self.explored_last_step: list[EffectCharacter] = []
        self.char_explore_order: list[EffectCharacter] = []
        self.complete = False

    def step(self) -> None:
        """Advance the traversal by one breadth-first layer.

        Each step consumes the current frontier, records any newly discovered
        linked neighbors, and stores those newly discovered characters as the
        next frontier.

        Note:
            `complete` becomes `True` only when `_frontier` is already empty at
            the start of a call.

        """
        self.explored_last_step.clear()
        if not self._frontier:
            self.complete = True
            return
        new_edges = []
        while self._frontier:
            position = self._frontier.pop(0)
            position_new_edges = [
                neighbor
                for neighbor in position.links
                if neighbor not in self._explored and neighbor not in self._frontier and neighbor not in new_edges
            ]
            new_edges.extend(position_new_edges)
            for character in position_new_edges:
                self._explored[character] = position
                self.explored_last_step.append(character)
                self.char_explore_order.append(character)
        self._frontier.extend(new_edges)
