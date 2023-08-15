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
    rowmerge,
)


def main():
    input_data = tops.get_piped_input()
    if not input_data:
        print("NO INPUT.")
    else:
        effect = rowmerge.RowMergeEffect(input_data, animation_rate=0.01)
        effect.run()


if __name__ == "__main__":
    main()
