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


@pytest.mark.parametrize(
    "color_code",
    [
        pytest.param("fgffff", id="non-hex-character"),
        pytest.param("fffff", id="too-short"),
        pytest.param("ffffff0", id="too-long"),
        pytest.param("#ffffffjunk", id="trailing-text"),
        pytest.param("ffffff#", id="trailing-hash"),
        pytest.param("##ffffff##", id="multiple-hashes"),
        pytest.param("+12345", id="leading-plus"),
        pytest.param("-12345", id="leading-minus"),
        pytest.param("\uff11\uff12\uff13\uff14\uff15\uff16", id="unicode-digits"),
    ],
)
def test_fg_invalid_hex(color_code: str) -> None:
    """Rejects malformed foreground hex color strings."""
    with pytest.raises(ValueError, match="Invalid RGB hex color code"):
        colorterm.fg(color_code)


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


@pytest.mark.parametrize("color_code", [True, False])
def test_fg_invalid_bool(color_code: bool) -> None:  # noqa: FBT001
    """Rejects boolean foreground color indexes."""
    with pytest.raises(
        TypeError,
        match=r"Color must be either hex string #000000 -> #FFFFFF or int xterm color code 0 <= n <= 255",
    ):
        colorterm.fg(color_code)


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


@pytest.mark.parametrize(
    "color_code",
    [
        pytest.param("fgffff", id="non-hex-character"),
        pytest.param("fffff", id="too-short"),
        pytest.param("ffffff0", id="too-long"),
        pytest.param("#ffffffjunk", id="trailing-text"),
        pytest.param("ffffff#", id="trailing-hash"),
        pytest.param("##ffffff##", id="multiple-hashes"),
        pytest.param("+12345", id="leading-plus"),
        pytest.param("-12345", id="leading-minus"),
        pytest.param("\uff11\uff12\uff13\uff14\uff15\uff16", id="unicode-digits"),
    ],
)
def test_bg_invalid_hex(color_code: str) -> None:
    """Rejects malformed background hex color strings."""
    with pytest.raises(ValueError, match="Invalid RGB hex color code"):
        colorterm.bg(color_code)


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


@pytest.mark.parametrize("color_code", [True, False])
def test_bg_invalid_bool(color_code: bool) -> None:  # noqa: FBT001
    """Rejects boolean background color indexes."""
    with pytest.raises(
        TypeError,
        match=r"Color must be either hex string #000000 -> #FFFFFF or int xterm color code 0 <= n <= 255",
    ):
        colorterm.bg(color_code)
