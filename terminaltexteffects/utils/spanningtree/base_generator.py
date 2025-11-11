"""Base spanning tree generator."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from terminaltexteffects.engine.terminal import Terminal


class SpanningTreeGenerator(ABC):
    """Base spanning tree generator."""

    def __init__(self, terminal: Terminal) -> None:
        """Initialize the tree generator.

        Args:
            terminal (Terminal): TTE Terminal

        """
        self.terminal = terminal

    @abstractmethod
    def step(self) -> None:
        """Progress the algorithm by one step."""
