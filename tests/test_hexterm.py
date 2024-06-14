import pytest
from terminaltexteffects.utils.hexterm import xterm_to_hex, is_valid_color

#Test suite made by Mihail-Dimosthenis Cretu

def test_xterm_to_hex_valid():
    assert xterm_to_hex(0) == "000000"
    assert xterm_to_hex(1) == "800000"
    assert xterm_to_hex(15) == "ffffff"

def test_xterm_to_hex_invalid():
    with pytest.raises(ValueError):
        xterm_to_hex(-1)
    with pytest.raises(ValueError):
        xterm_to_hex(256)

def test_is_valid_color_invalid_characters():
    # Test invalid hex color strings containing invalid characters
    assert is_valid_color("#12345G") == False
    assert is_valid_color("#12#456") == False
    assert is_valid_color("#12345Z") == False
    assert is_valid_color("#12-456") == False

def test_is_valid_color_too_long():
    # Test invalid hex color strings that are too long
    assert is_valid_color("#12345670000000") == False
    assert is_valid_color("#12345678900000") == False

def test_is_valid_color_not_string():
    # Test invalid hex color strings that are empty
    assert is_valid_color(122) == True


