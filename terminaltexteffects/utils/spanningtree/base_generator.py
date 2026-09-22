"""Base spanning tree generator."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from terminaltexteffects.engine.base_character import EffectCharacter
    from terminaltexteffects.engine.terminal import Terminal


class SpanningTreeGenerator(ABC):
    """Abstract base class for spanning-tree and graph-traversal generators."""

    def __init__(self, terminal: Terminal) -> None:
        """Initialize the tree generator.

        Args:
            terminal (Terminal): TTE terminal used as the source of characters,
                neighbor relationships, and text-boundary checks.

        """
        self.terminal = terminal

    def get_neighbors(
        self,
        character: EffectCharacter,
        *,
        unlinked_only: bool = True,
        limit_to_text_boundary: bool = False,
    ) -> list[EffectCharacter]:
        """Get the neighbors for a given character and apply filters.

        Args:
            character (EffectCharacter): Subject character.
            unlinked_only (bool, optional): If True, filter out any neighbors with
                links. If False, include both linked and unlinked neighbors.
                Defaults to True.
            limit_to_text_boundary (bool, optional): If True, filter out neighbors outside the text boundary.
                Defaults to False.

        Returns:
            list[EffectCharacter]: List of EffectCharacter neighbors.

        """
        neighbors = [neighbor for neighbor in character.neighbors.values() if neighbor]
        if limit_to_text_boundary:
            neighbors = [
                neighbor for neighbor in neighbors if self.terminal.canvas.coord_is_in_text(neighbor.input_coord)
            ]
        if unlinked_only:
            neighbors = [neighbor for neighbor in neighbors if not neighbor.links]
        return neighbors

    @staticmethod
    def _require_unlinked(character: EffectCharacter) -> None:
        """Reject character state left by an earlier tree-generation run."""
        if character.links:
            msg = f"Cannot generate a spanning tree from pre-linked character {character!r}."
            raise ValueError(msg)

    def _get_unvisited_neighbors(
        self,
        character: EffectCharacter,
        visited_chars: set[EffectCharacter],
        *,
        limit_to_text_boundary: bool = False,
    ) -> list[EffectCharacter]:
        """Return eligible neighbors using generator-owned visitation state.

        Raises:
            ValueError: An unvisited neighbor contains links from an earlier tree-generation run.

        """
        unvisited_neighbors: list[EffectCharacter] = []
        for neighbor in self.get_neighbors(
            character,
            unlinked_only=False,
            limit_to_text_boundary=limit_to_text_boundary,
        ):
            if neighbor in visited_chars:
                continue
            self._require_unlinked(neighbor)
            unvisited_neighbors.append(neighbor)
        return unvisited_neighbors

    @abstractmethod
    def step(self) -> None:
        """Progress the algorithm by one step."""
