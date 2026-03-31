"""Tests for terminal color escape sequence helpers."""

import pytest

from terminaltexteffects.utils import colorterm

pytestmark = [pytest.mark.utils, pytest.mark.smoke]


def test_fg_hex_with_hash() -> None:
    """Formats a foreground ANSI sequence from a hashed hex string."""
    assert colorterm.fg("#ffffff") == "\x1b[38;2;255;255;255m"


def test_fg_hex_min_with_hash() -> None:
    """Formats a foreground ANSI sequence from the minimum hashed hex string."""
    assert colorterm.fg("#000000") == "\x1b[38;2;0;0;0m"


def test_fg_hex() -> None:
    """Formats a foreground ANSI sequence from a plain hex string."""
    assert colorterm.fg("ffffff") == "\x1b[38;2;255;255;255m"


def test_fg_hex_min() -> None:
    """Formats a foreground ANSI sequence from the minimum plain hex string."""
    assert colorterm.fg("000000") == "\x1b[38;2;0;0;0m"


def test_fg_xterm() -> None:
    """Formats a foreground ANSI sequence from an xterm color index."""
    assert colorterm.fg(255) == "\x1b[38;5;255m"


def test_fg_xterm_min() -> None:
    """Formats a foreground ANSI sequence from the minimum xterm color index."""
    assert colorterm.fg(0) == "\x1b[38;5;0m"


def test_fg_invalid_hex() -> None:
    """Rejects malformed foreground hex color strings."""
    with pytest.raises(ValueError):
        colorterm.fg("fgffff")


def test_fg_invalid_xterm() -> None:
    """Rejects out-of-range foreground xterm color indexes."""
    with pytest.raises(ValueError):
        colorterm.fg(256)


def test_fg_invalid_type() -> None:
    """Rejects unsupported foreground color input types."""
    with pytest.raises(TypeError):
        colorterm.fg(3.14)  # type: ignore[arg-type]


def test_bg_hex_with_hash() -> None:
    """Formats a background ANSI sequence from a hashed hex string."""
    assert colorterm.bg("#ffffff") == "\x1b[48;2;255;255;255m"


def test_bg_hex_min_with_hash() -> None:
    """Formats a background ANSI sequence from the minimum hashed hex string."""
    assert colorterm.bg("#000000") == "\x1b[48;2;0;0;0m"


def test_bg_hex() -> None:
    """Formats a background ANSI sequence from a plain hex string."""
    assert colorterm.bg("ffffff") == "\x1b[48;2;255;255;255m"


def test_bg_hex_min() -> None:
    """Formats a background ANSI sequence from the minimum plain hex string."""
    assert colorterm.bg("000000") == "\x1b[48;2;0;0;0m"


def test_bg_xterm() -> None:
    """Formats a background ANSI sequence from an xterm color index."""
    assert colorterm.bg(255) == "\x1b[48;5;255m"


def test_bg_xterm_min() -> None:
    """Formats a background ANSI sequence from the minimum xterm color index."""
    assert colorterm.bg(0) == "\x1b[48;5;0m"


def test_bg_invalid_hex() -> None:
    """Rejects malformed background hex color strings."""
    with pytest.raises(ValueError):
        colorterm.bg("fgffff")


def test_bg_invalid_xterm() -> None:
    """Rejects out-of-range background xterm color indexes."""
    with pytest.raises(ValueError):
        colorterm.bg(256)


def test_bg_invalid_type() -> None:
    """Rejects unsupported background color input types."""
    with pytest.raises(TypeError):
        colorterm.bg(3.14)  # type: ignore[arg-type]
