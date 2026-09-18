"""Helpers for validating symbols and measuring their terminal-cell width."""

from __future__ import annotations

import unicodedata
from functools import lru_cache

from terminaltexteffects.utils.exceptions import InvalidSymbolError


@lru_cache(maxsize=1024)
def _get_non_ascii_symbol_cell_width(symbol: str) -> int:
    """Validate and measure a symbol that did not match the printable ASCII fast path."""
    if len(symbol) != 1 or not symbol.isprintable() or unicodedata.category(symbol).startswith("M"):
        raise InvalidSymbolError(symbol)
    return 2 if unicodedata.east_asian_width(symbol) in {"F", "W"} else 1


def get_symbol_cell_width(symbol: str) -> int:
    """Return the terminal-cell width of a valid `EffectCharacter` symbol.

    Symbols are limited to one printable Unicode code point. East Asian wide and
    full-width code points occupy two cells; all other accepted symbols occupy one.

    Args:
        symbol (str): Symbol to validate and measure.

    Raises:
        InvalidSymbolError: If `symbol` is empty, contains multiple code points, or
            cannot be rendered independently in a terminal cell.

    Returns:
        int: One or two terminal cells.

    """
    if len(symbol) == 1 and " " <= symbol <= "~":
        return 1
    return _get_non_ascii_symbol_cell_width(symbol)
