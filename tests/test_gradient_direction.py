import pytest
import argparse
from terminaltexteffects.utils.argvalidators import GradientDirection  
from terminaltexteffects.utils.graphics import Gradient  

def test_valid_gradient_direction_horizontal():
    assert GradientDirection.type_parser("horizontal") == Gradient.Direction.HORIZONTAL

def test_valid_gradient_direction_vertical():
    assert GradientDirection.type_parser("vertical") == Gradient.Direction.VERTICAL

def test_valid_gradient_direction_diagonal():
    assert GradientDirection.type_parser("diagonal") == Gradient.Direction.DIAGONAL

def test_valid_gradient_direction_radial():
    assert GradientDirection.type_parser("radial") == Gradient.Direction.RADIAL

def test_invalid_gradient_direction():
    with pytest.raises(argparse.ArgumentTypeError):
        GradientDirection.type_parser("invalid_direction")
