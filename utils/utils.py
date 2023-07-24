from dataclasses import dataclass


@dataclass
class Character:
    """A character symbol and its coordinates, y as number of rows above the current cursor position."""

    symbol: str
    x: int
    y: int


def decompose_input(input_data: str) -> list[Character]:
    """Decomposes the output into a list of Character objects containing the symbol and the relative position.

    Args:
        input_data (str): string from stdin

    Returns:
        list[Character]: list of tuples containing Character objects
    """
    output_lines = input_data.splitlines()
    output_height = len(output_lines)
    output_characters = []
    for y, line in enumerate(output_lines):
        for x, symbol in enumerate(line):
            if symbol != " ":
                output_characters.append(Character(symbol, x + 1, output_height - y))
    return output_characters
