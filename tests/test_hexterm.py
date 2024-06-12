import pytest
from terminaltexteffects.utils.hexterm import xterm_to_hex, is_valid_color

#Test suite made by Mihail-Dimosthenis Cretu

def test_xterm_to_hex_valid():
    assert xterm_to_hex(0) == "000000"
    assert xterm_to_hex(1) == "#800000"
    assert xterm_to_hex(15) == "#ffffff"

def test_xterm_to_hex_invalid():
    with pytest.raises(ValueError):
        xterm_to_hex(-1)
    with pytest.raises(ValueError):
        xterm_to_hex(256)

def test_is_valid_color_valid():
    # Test valid hex color strings
    assert is_valid_color("#000000") == True
    assert is_valid_color("#FFFFFF") == True
    assert is_valid_color("#123ABC") == True
    assert is_valid_color("#abcdef") == True
    # Test valid colors within the 256 range
    assert is_valid_color("#0000FF") == True
    assert is_valid_color("#00FF00") == True
    assert is_valid_color("#FF0000") == True

def test_is_valid_color_missing_hash():
    # Test invalid hex color strings missing '#'
    assert is_valid_color("123ABC") == False
    assert is_valid_color("FFFFFF") == False

def test_is_valid_color_too_short():
    # Test invalid hex color strings that are too short
    assert is_valid_color("#FFF") == False
    assert is_valid_color("#123") == False

def test_is_valid_color_invalid_characters():
    # Test invalid hex color strings containing invalid characters
    assert is_valid_color("#12345G") == False
    assert is_valid_color("#12#456") == False
    assert is_valid_color("#12345Z") == False
    assert is_valid_color("#12-456") == False

def test_is_valid_color_too_long():
    # Test invalid hex color strings that are too long
    assert is_valid_color("#1234567") == False
    assert is_valid_color("#1234567890") == False
