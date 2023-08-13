import terminaltexteffects.utils.terminaloperations as tops
from terminaltexteffects.effects import (
    expand,
    pour,
    random_sequence,
    scattered,
    sparkler,
    rain,
    decrypt,
    shootingstar,
    rowslide,
    columnslide,
    verticalslice,
)


def main():
    input_data = tops.get_piped_input()
    if not input_data:
        input_data = "NO INPUT."


if __name__ == "__main__":
    main()
