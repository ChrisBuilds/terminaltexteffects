import pytest
import math
from terminaltexteffects.utils.easing import in_elastic 

def test_in_elastic_zero():
    assert in_elastic(0) == 0

def test_in_elastic_one():
    assert in_elastic(1) == 1

def test_in_elastic_mid():
    # Calculate expected value manually if needed
    progress_ratio = 0.5
    c4 = (2 * math.pi) / 3
    expected_value = -(2 ** (10 * progress_ratio - 10)) * math.sin((progress_ratio * 10 - 10.75) * c4)
    assert in_elastic(progress_ratio) == pytest.approx(expected_value)

def test_in_elastic_near_zero():
    progress_ratio = 0.01
    c4 = (2 * math.pi) / 3
    expected_value = -(2 ** (10 * progress_ratio - 10)) * math.sin((progress_ratio * 10 - 10.75) * c4)
    assert in_elastic(progress_ratio) == pytest.approx(expected_value)

def test_in_elastic_near_one():
    progress_ratio = 0.99
    c4 = (2 * math.pi) / 3
    expected_value = -(2 ** (10 * progress_ratio - 10)) * math.sin((progress_ratio * 10 - 10.75) * c4)
    assert in_elastic(progress_ratio) == pytest.approx(expected_value)
