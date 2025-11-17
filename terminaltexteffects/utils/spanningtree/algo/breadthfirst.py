"""Breadth-First algorithm implementation.

Classes:
BreadthFirst: Breadth-First spanning algorithm.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from terminaltexteffects.utils.spanningtree.base_generator import SpanningTreeGenerator

if TYPE_CHECKING:
    from terminaltexteffects.engine.base_character import EffectCharacter
    from terminaltexteffects.engine.terminal import Terminal


class BreadthFirst(SpanningTreeGenerator):
    """Breadth-First algorithm.

    Uses the breadth-first algorithm to explore a graph.

    Attributes:
        explored_last_step (list[EffectCharacter]): Characters explored in the last step.
        char_explore_order (list[EffectCharacter]): Characters in the order they were explored.
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
            limit_to_text_boundary (bool, optional): If True, the starting character, if not provided, will
                be chosen within the text boundary. This should be True of the spanning tree was generated
                with limit_to_text_boundary=True.

        Raises:
            ValueError: Unable to find a starting character.

        """
        super().__init__(terminal)
        self._limit_to_text_boundary = limit_to_text_boundary
        self.starting_char = starting_char or terminal.get_character_by_input_coord(
            terminal.canvas.random_coord(within_text_boundary=limit_to_text_boundary),
        )
        if starting_char is None:
            msg = "Unable to find a starting character."
            raise ValueError(msg)
        self._frontier = [starting_char]
        self._explored: dict[EffectCharacter, EffectCharacter] = {starting_char: starting_char}
        self.explored_last_step: list[EffectCharacter] = []
        self.char_explore_order: list[EffectCharacter] = []
        self.complete = False

    def step(self) -> None:
        """Perform a single step of the algorithm."""
        self.explored_last_step.clear()
        if not self._frontier:
            self.complete = True
            return
        new_edges = []
        while self._frontier:
            position = self._frontier.pop(0)
            new_edges.extend(
                [
                    neighbor
                    for neighbor in position.links
                    if neighbor not in self._explored and neighbor not in self._frontier
                ],
            )
            for character in new_edges:
                self._explored[character] = position
                self.explored_last_step.append(character)
                self.char_explore_order.append(character)
        self._frontier.extend(new_edges)
