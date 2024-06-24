import pytest
from terminaltexteffects.utils import colorterm

# Branch coverage dictionary
branch_coverage = {}

def track_coverage(branch_name):
    branch_coverage[branch_name] = True

# Initialize branch coverage with all branches set to False (not hit)
def initialize_branch_coverage():
    global branch_coverage
    branch_coverage = {
        "color_fg_hex": False,
        "color_fg_int": False,
        "color_fg_invalid_hex": False,
        "color_fg_invalid_int": False,
        "color_fg_invalid_type": False,
        "color_bg_hex": False,
        "color_bg_int": False,
        "color_bg_invalid_hex": False,
        "color_bg_invalid_int": False,
        "color_bg_invalid_type": False,
    }

# Tests
def test_fg_with_valid_hex_strings():
    # Test with valid hex color strings
    assert colorterm.fg("ffffff") == "\x1b[38;2;255;255;255m"
    assert colorterm.fg("000000") == "\x1b[38;2;0;0;0m"
    assert colorterm.fg("123456") == "\x1b[38;2;18;52;86m"
    track_coverage("color_fg_hex")

def test_fg_with_valid_int_values():
    # Test with valid xterm color integers
    assert colorterm.fg(255) == "\x1b[38;5;255m"
    assert colorterm.fg(0) == "\x1b[38;5;0m"
    assert colorterm.fg(127) == "\x1b[38;5;127m"
    track_coverage("color_fg_int")

def test_fg_with_invalid_hex_strings():
    # Test with invalid hex color strings
    with pytest.raises(ValueError):
        colorterm.fg("invalid")
    with pytest.raises(ValueError):
        colorterm.fg("#GGGGGG")
    with pytest.raises(ValueError):
        colorterm.fg("12345G")
    track_coverage("color_fg_invalid_hex")

def test_fg_with_invalid_int_values():
    # Test with invalid xterm color integers
    with pytest.raises(ValueError):
        colorterm.fg(256)
    with pytest.raises(ValueError):
        colorterm.fg(-1)
    track_coverage("color_fg_invalid_int")

def test_fg_with_invalid_type():
    # Test with an invalid color type
    with pytest.raises(ValueError):
        colorterm.fg([255, 255, 255])
    with pytest.raises(ValueError):
        colorterm.fg(None)
    with pytest.raises(ValueError):
        colorterm.fg(12.34)
    track_coverage("color_fg_invalid_type")

def test_bg_with_valid_hex_strings():
    # Test with valid hex color strings
    assert colorterm.bg("ffffff") == "\x1b[48;2;255;255;255m"
    assert colorterm.bg("000000") == "\x1b[48;2;0;0;0m"
    assert colorterm.bg("123456") == "\x1b[48;2;18;52;86m"
    track_coverage("color_bg_hex")

def test_bg_with_valid_int_values():
    # Test with valid xterm color integers
    assert colorterm.bg(255) == "\x1b[48;5;255m"
    assert colorterm.bg(0) == "\x1b[48;5;0m"
    assert colorterm.bg(127) == "\x1b[48;5;127m"
    track_coverage("color_bg_int")

def test_bg_with_invalid_hex_strings():
    # Test with invalid hex color strings
    with pytest.raises(ValueError):
        colorterm.bg("invalid")
    with pytest.raises(ValueError):
        colorterm.bg("#GGGGGG")
    with pytest.raises(ValueError):
        colorterm.bg("12345G")
    track_coverage("color_bg_invalid_hex")

def test_bg_with_invalid_int_values():
    # Test with invalid xterm color integers
    with pytest.raises(ValueError):
        colorterm.bg(256)
    with pytest.raises(ValueError):
        colorterm.bg(-1)
    track_coverage("color_bg_invalid_int")

def test_bg_with_invalid_type():
    # Test with an invalid color type
    with pytest.raises(ValueError):
        colorterm.bg([255, 255, 255])
    with pytest.raises(ValueError):
        colorterm.bg(None)
    with pytest.raises(ValueError):
        colorterm.bg(12.34)
    track_coverage("color_bg_invalid_type")

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

def print_coverage():
    method_branches = {
        "fg": ["color_fg_hex", "color_fg_int", "color_fg_invalid_hex", "color_fg_invalid_int", "color_fg_invalid_type"],
        "bg": ["color_bg_hex", "color_bg_int", "color_bg_invalid_hex", "color_bg_invalid_int", "color_bg_invalid_type"]
    }
    
    for method, branches in method_branches.items():
        hit_branches = sum(branch_coverage.get(branch, False) for branch in branches)
        total_branches = len(branches)
        coverage_percentage = (hit_branches / total_branches) * 100
        print(f"Coverage for {method}: {hit_branches}/{total_branches} branches hit ({coverage_percentage:.2f}%)")
        for branch in branches:
            print(f"  {branch} was {'hit' if branch_coverage.get(branch, False) else 'not hit'}")

def run_tests():
    initialize_branch_coverage()
    test_fg_with_valid_hex_strings()
    test_fg_with_valid_int_values()
    test_fg_with_invalid_hex_strings()
    test_fg_with_invalid_int_values()
    test_fg_with_invalid_type()
    test_bg_with_valid_hex_strings()
    test_bg_with_valid_int_values()
    test_bg_with_invalid_hex_strings()
    test_bg_with_invalid_int_values()
    test_bg_with_invalid_type()
    test_fg_edge_cases()
    test_bg_edge_cases()

if __name__ == "__main__":
    run_tests()
    print_coverage()
