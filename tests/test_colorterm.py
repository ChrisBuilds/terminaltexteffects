import pytest
from terminaltexteffects.utils import colorterm

def test_fg_with_valid_hex_strings():
    # Test with valid hex color strings
    assert colorterm.fg("ffffff") == "\x1b[38;2;255;255;255m"
    assert colorterm.fg("000000") == "\x1b[38;2;0;0;0m"
    assert colorterm.fg("123456") == "\x1b[38;2;18;52;86m"

def test_fg_with_valid_int_values():
    # Test with valid xterm color integers
    assert colorterm.fg(255) == "\x1b[38;5;255m"
    assert colorterm.fg(0) == "\x1b[38;5;0m"
    assert colorterm.fg(127) == "\x1b[38;5;127m"

def test_fg_with_invalid_hex_strings():
    # Test with invalid hex color strings
    with pytest.raises(ValueError):
        colorterm.fg("invalid")
    with pytest.raises(ValueError):
        colorterm.fg("#GGGGGG")
    with pytest.raises(ValueError):
        colorterm.fg("12345G")

def test_fg_with_invalid_int_values():
    # Test with invalid xterm color integers
    with pytest.raises(ValueError):
        colorterm.fg(256)
    with pytest.raises(ValueError):
        colorterm.fg(-1)

def test_fg_with_invalid_type():
    # Test with an invalid color type
    with pytest.raises(ValueError):
        colorterm.fg([255, 255, 255])
    with pytest.raises(ValueError):
        colorterm.fg(None)
    with pytest.raises(ValueError):
        colorterm.fg(12.34)

def test_bg_with_valid_hex_strings():
    # Test with valid hex color strings
    assert colorterm.bg("ffffff") == "\x1b[48;2;255;255;255m"
    assert colorterm.bg("000000") == "\x1b[48;2;0;0;0m"
    assert colorterm.bg("123456") == "\x1b[48;2;18;52;86m"

def test_bg_with_valid_int_values():
    # Test with valid xterm color integers
    assert colorterm.bg(255) == "\x1b[48;5;255m"
    assert colorterm.bg(0) == "\x1b[48;5;0m"
    assert colorterm.bg(127) == "\x1b[48;5;127m"

def test_bg_with_invalid_hex_strings():
    # Test with invalid hex color strings
    with pytest.raises(ValueError):
        colorterm.bg("invalid")
    with pytest.raises(ValueError):
        colorterm.bg("#GGGGGG")
    with pytest.raises(ValueError):
        colorterm.bg("12345G")

def test_bg_with_invalid_int_values():
    # Test with invalid xterm color integers
    with pytest.raises(ValueError):
        colorterm.bg(256)
    with pytest.raises(ValueError):
        colorterm.bg(-1)

def test_bg_with_invalid_type():
    # Test with an invalid color type
    with pytest.raises(ValueError):
        colorterm.bg([255, 255, 255])
    with pytest.raises(ValueError):
        colorterm.bg(None)
    with pytest.raises(ValueError):
        colorterm.bg(12.34)

# Additional tests to ensure edge cases are handled
def test_fg_edge_cases():
    # Edge case with hex color string without hash
    assert colorterm.fg("ffffff") == "\x1b[38;2;255;255;255m"
    
    # Edge case with hex color string with hash
    assert colorterm.fg("#000000") == "\x1b[38;2;0;0;0m"
    
    # Edge case with the lowest and highest valid xterm color integers
    assert colorterm.fg(0) == "\x1b[38;5;0m"
    assert colorterm.fg(255) == "\x1b[38;5;255m"

def test_bg_edge_cases():
    # Edge case with hex color string without hash
    assert colorterm.bg("ffffff") == "\x1b[48;2;255;255;255m"
    
    # Edge case with hex color string with hash
    assert colorterm.bg("#000000") == "\x1b[48;2;0;0;0m"
    
    # Edge case with the lowest and highest valid xterm color integers
    assert colorterm.bg(0) == "\x1b[48;5;0m"
    assert colorterm.bg(255) == "\x1b[48;5;255m"
