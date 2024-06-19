import pytest
from argparse import ArgumentTypeError
from terminaltexteffects.utils.argvalidators import PositiveFloat
from terminaltexteffects.utils.hexterm import xterm_to_hex, is_valid_color

#Test suite made by Mihail-Dimosthenis Cretu

def test_type_parser_valid():
    assert PositiveFloat.type_parser("1.23") == 1.23
    assert PositiveFloat.type_parser("10") == 10.0

def test_type_parser_invalid():
    with pytest.raises(ArgumentTypeError):
        PositiveFloat.type_parser("-1")
    with pytest.raises(ValueError):
        PositiveFloat.type_parser("abc")
    with pytest.raises(ValueError): 
        PositiveFloat.type_parser("")

def test_xterm_to_hex_valid():
    assert xterm_to_hex(0) == "000000"
    assert xterm_to_hex(1) == "800000"
    assert xterm_to_hex(15) == "ffffff"

def test_xterm_to_hex_invalid():
    with pytest.raises(ValueError):
        xterm_to_hex(-1)
    with pytest.raises(ValueError):
        xterm_to_hex(256)

def test_is_valid_color_invalid_length():
    assert is_valid_color("#FFF") == False
    assert is_valid_color("#123") == False    
    assert is_valid_color("#12345670000000") == False
    assert is_valid_color("#12345678900000") == False

def test_is_valid_color_invalid_characters():
    assert is_valid_color("#1234!@") == False

def test_is_valid_color_number():
    assert is_valid_color(122) == True
    assert is_valid_color(256) == False