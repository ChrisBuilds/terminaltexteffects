from effects.effect_char import EffectCharacter


def decompose_input(input_data: str) -> list[EffectCharacter]:
    """Decomposes the output into a list of Character objects containing the symbol and its row/column coordinates
    relative to the input input display location.

    Coordinates are relative to the cursor row position at the time of execution. 1,1 is the bottom left corner of the row
    above the cursor.

    Args:
        input_data (str): string from stdin

    Returns:
        list[Character]: list EffectCharacter objects
    """
    output_lines = input_data.splitlines()
    input_height = len(output_lines)
    output_characters = []
    for row, line in enumerate(output_lines):
        for column, symbol in enumerate(line):
            if symbol != " ":
                output_characters.append(EffectCharacter(symbol, column + 1, input_height - row))
    return output_characters
