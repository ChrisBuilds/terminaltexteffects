"""Base spanning tree generator."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from terminaltexteffects.engine.base_character import EffectCharacter
    from terminaltexteffects.engine.terminal import Terminal


class SpanningTreeGenerator(ABC):
    """Base spanning tree generator."""

    def __init__(self, terminal: Terminal) -> None:
        """Initialize the tree generator.

        Args:
            terminal (Terminal): TTE Terminal

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
            unlinked_only (bool, optional): If True, filter out any neighbors with links. Defaults to True.
            limit_to_text_boundary (bool, optional): If True, filter out neighbors outside the text boundary.
                Defaults to False.

        Returns:
            list[EffectCharacter]: List of EffectCharacter neighbors.

        """
        neighbors = [neighbor for neighbor in character.neighbors.values() if neighbor and not neighbor.links]
        if limit_to_text_boundary:
            neighbors = [
                neighbor for neighbor in neighbors if self.terminal.canvas.coord_is_in_text(neighbor.input_coord)
            ]
        if unlinked_only:
            neighbors = [neighbor for neighbor in neighbors if not neighbor.links]
        return neighbors

    @abstractmethod
    def step(self) -> None:
        """Progress the algorithm by one step."""
