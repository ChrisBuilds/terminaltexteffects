"""Helpers for validating symbols and measuring their terminal-cell width."""

from __future__ import annotations

import unicodedata

from terminaltexteffects.utils.exceptions import InvalidSymbolError


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
    if len(symbol) != 1 or not symbol.isprintable() or unicodedata.category(symbol).startswith("M"):
        raise InvalidSymbolError(symbol)
    return 2 if unicodedata.east_asian_width(symbol) in {"F", "W"} else 1
