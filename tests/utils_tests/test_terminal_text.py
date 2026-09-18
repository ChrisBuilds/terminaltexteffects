"""Tests for terminal-symbol validation and display-width measurement."""

import pytest

from terminaltexteffects.utils import terminal_text


def test_ascii_width_fast_path_avoids_unicode_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """Printable ASCII symbols should not require Unicode metadata lookups."""

    def fail_lookup(_symbol: str) -> str:
        message = "ASCII width used the Unicode database"
        raise AssertionError(message)

    monkeypatch.setattr(terminal_text.unicodedata, "category", fail_lookup)
    monkeypatch.setattr(terminal_text.unicodedata, "east_asian_width", fail_lookup)

    assert terminal_text.get_symbol_cell_width("A") == 1
    assert terminal_text.get_symbol_cell_width(" ") == 1


def test_non_ascii_width_measurement_is_cached() -> None:
    """Repeated non-ASCII symbols should reuse their validated display width."""
    terminal_text._get_non_ascii_symbol_cell_width.cache_clear()

    assert terminal_text.get_symbol_cell_width("界") == 2
    assert terminal_text.get_symbol_cell_width("界") == 2

    cache_info = terminal_text._get_non_ascii_symbol_cell_width.cache_info()
    assert (cache_info.hits, cache_info.misses) == (1, 1)
