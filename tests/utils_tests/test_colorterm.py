"""Tests for terminal color escape sequence helpers."""

from __future__ import annotations

import pytest

from terminaltexteffects.utils import colorterm

pytestmark = [pytest.mark.utils, pytest.mark.smoke]


@pytest.mark.parametrize(
    ("color_code", "expected_sequence"),
    [
        pytest.param("#ffffff", "\x1b[38;2;255;255;255m", id="hex-with-hash-max"),
        pytest.param("#000000", "\x1b[38;2;0;0;0m", id="hex-with-hash-min"),
        pytest.param("ffffff", "\x1b[38;2;255;255;255m", id="hex-max"),
        pytest.param("000000", "\x1b[38;2;0;0;0m", id="hex-min"),
        pytest.param(255, "\x1b[38;5;255m", id="xterm-max"),
        pytest.param(0, "\x1b[38;5;0m", id="xterm-min"),
    ],
)
def test_fg_valid_color_codes(color_code: str | int, expected_sequence: str) -> None:
    """Formats foreground ANSI sequences for valid hex and xterm color inputs."""
    assert colorterm.fg(color_code) == expected_sequence


def test_fg_invalid_hex() -> None:
    """Rejects malformed foreground hex color strings."""
    with pytest.raises(ValueError, match="invalid literal for int\\(\\) with base 16"):
        colorterm.fg("fgffff")


@pytest.mark.parametrize("color_code", [pytest.param(256, id="above-max"), pytest.param(-1, id="below-min")])
def test_fg_invalid_xterm(color_code: int) -> None:
    """Rejects out-of-range foreground xterm color indexes."""
    with pytest.raises(
        ValueError,
        match=r"xterm color codes must be an integer: 0 <= n <= 255",
    ):
        colorterm.fg(color_code)


def test_fg_invalid_type() -> None:
    """Rejects unsupported foreground color input types."""
    with pytest.raises(
        TypeError,
        match=r"Color must be either hex string #000000 -> #FFFFFF or int xterm color code 0 <= n <= 255",
    ):
        colorterm.fg(3.14)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("color_code", "expected_sequence"),
    [
        pytest.param("#ffffff", "\x1b[48;2;255;255;255m", id="hex-with-hash-max"),
        pytest.param("#000000", "\x1b[48;2;0;0;0m", id="hex-with-hash-min"),
        pytest.param("ffffff", "\x1b[48;2;255;255;255m", id="hex-max"),
        pytest.param("000000", "\x1b[48;2;0;0;0m", id="hex-min"),
        pytest.param(255, "\x1b[48;5;255m", id="xterm-max"),
        pytest.param(0, "\x1b[48;5;0m", id="xterm-min"),
    ],
)
def test_bg_valid_color_codes(color_code: str | int, expected_sequence: str) -> None:
    """Formats background ANSI sequences for valid hex and xterm color inputs."""
    assert colorterm.bg(color_code) == expected_sequence


def test_bg_invalid_hex() -> None:
    """Rejects malformed background hex color strings."""
    with pytest.raises(ValueError, match="invalid literal for int\\(\\) with base 16"):
        colorterm.bg("fgffff")


@pytest.mark.parametrize("color_code", [pytest.param(256, id="above-max"), pytest.param(-1, id="below-min")])
def test_bg_invalid_xterm(color_code: int) -> None:
    """Rejects out-of-range background xterm color indexes."""
    with pytest.raises(
        ValueError,
        match=r"xterm color codes must be an integer: 0 <= n <= 255",
    ):
        colorterm.bg(color_code)


def test_bg_invalid_type() -> None:
    """Rejects unsupported background color input types."""
    with pytest.raises(
        TypeError,
        match=r"Color must be either hex string #000000 -> #FFFFFF or int xterm color code 0 <= n <= 255",
    ):
        colorterm.bg(3.14)  # type: ignore[arg-type]
