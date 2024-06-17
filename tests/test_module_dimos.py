# my_module.py
from argparse import ArgumentTypeError
import argparse
import pytest

branch_coverage = {}

def track_coverage(branch_name):
    branch_coverage[branch_name] = True

# Initialize branch coverage with all branches set to False (not hit)
def initialize_branch_coverage():
    global branch_coverage
    branch_coverage = {
        "xterm_to_hex_not_in_map": False,
        "xterm_to_hex_in_map": False,
        "is_valid_color_is_str": False,
        "is_valid_color_not_str": False,
        "is_valid_color_invalid_len": False,
        "is_valid_color_valid_len": False,
        "is_valid_color_value_error": False,
        "is_valid_color_valid_str": False,
        "type_parser_valid_float": False,
        "type_parser_invalid_float": False
    }

xterm_to_hex_map = {
    0: "#000000", 1: "#800000", 2: "#008000", 3: "#808000",
    4: "#000080", 5: "#800080", 6: "#008080", 7: "#c0c0c0",
    8: "#808080", 9: "#ff0000", 10: "#00ff00", 11: "#ffff00",
    12: "#0000ff", 13: "#ff00ff", 14: "#00ffff", 15: "#ffffff",
}

def xterm_to_hex(xterm_color: int) -> str:
    if xterm_color not in xterm_to_hex_map:
        track_coverage("xterm_to_hex_not_in_map")
        raise ValueError(f"Invalid XTerm-256 color code: {xterm_color}")
    else:
        track_coverage("xterm_to_hex_in_map")
    return xterm_to_hex_map[xterm_color].strip("#")

def is_valid_color(color: int | str) -> bool:
    if isinstance(color, str):
        track_coverage("is_valid_color_is_str")
        if len(color) not in [6, 7]:
            track_coverage("is_valid_color_invalid_len")
            return False
        try:
            track_coverage("is_valid_color_valid_len")
            int(color.strip("#"), 16)
        except ValueError:
            track_coverage("is_valid_color_value_error")
            return False
        track_coverage("is_valid_color_valid_str")
        return True
    else:
        track_coverage("is_valid_color_not_str")
        return color in range(256)

class PositiveFloat:
    @staticmethod
    def type_parser(arg: str) -> float:
        if float(arg) > 0:
            track_coverage("type_parser_valid_float")
            return float(arg)
        else:
            track_coverage("type_parser_invalid_float")
            raise argparse.ArgumentTypeError(
                f"invalid value: '{arg}' is not a valid value. Argument must be a float > 0."
            )

def print_coverage():
    for branch, hit in branch_coverage.items():
        print(f"{branch} was {'hit' if hit else 'not hit'}")


def test_module_dimos():
    initialize_branch_coverage()
#Test suites

    #PositiveFloat test suite
    PositiveFloat.type_parser("1.23") #valid float
    with pytest.raises(ArgumentTypeError):#invalid float
        PositiveFloat.type_parser("-1")

    #PositiveFloat test suite
    xterm_to_hex(0)#valid xterm color
    with pytest.raises(ValueError):#invalid xterm color
        xterm_to_hex(-1)

    #is_valid_color test suite
    is_valid_color("#123456") #valid color
    is_valid_color("#12345G") #invalid color
    is_valid_color("#12345670000000") #invalid length
    is_valid_color(122) # number is in range
    is_valid_color(256) # number is not in range


if __name__ == "__main__":
    test_module_dimos()
    print_coverage()
