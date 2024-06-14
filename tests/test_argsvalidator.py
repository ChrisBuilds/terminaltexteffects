import pytest
from argparse import ArgumentTypeError
from terminaltexteffects.utils.argvalidators import PositiveFloat

#Test suite made by Mihail-Dimosthenis Cretu

def test_type_parser_valid():
    # Test valid positive float strings
    assert PositiveFloat.type_parser("1.23") == 1.23
    assert PositiveFloat.type_parser("10") == 10.0
    assert PositiveFloat.type_parser("0.1") == 0.1

def test_type_parser_invalid():
    # Test invalid float strings
    with pytest.raises(ArgumentTypeError):
        PositiveFloat.type_parser("-1")
    with pytest.raises(ArgumentTypeError):
        PositiveFloat.type_parser("0")
    with pytest.raises(ValueError):  # Catch ValueError raised by float conversion before ArgumentTypeError
        PositiveFloat.type_parser("abc")
    with pytest.raises(ValueError):  # Catch ValueError raised by float conversion before ArgumentTypeError
        PositiveFloat.type_parser("")
