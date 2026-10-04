"""Test character sort argument parsing and completion."""

import pytest

from terminaltexteffects.utils.argutils import CharacterSort, CharacterSortArg

pytestmark = [pytest.mark.utils, pytest.mark.smoke]


@pytest.mark.parametrize("sort", list(CharacterSort))
def test_character_sort_parser_and_completion(sort: CharacterSort) -> None:
    """Every sort is available through both CLI parsing and shell completion."""
    assert CharacterSortArg.type_parser(sort.name.lower()) is sort
    assert CharacterSortArg.type_parser(sort.name) is sort
    assert CharacterSortArg.type_parser(sort) is sort
    assert sort.name.lower() in CharacterSortArg.COMPLETION_CHOICES


@pytest.mark.parametrize(
    ("key", "sort"),
    [
        ("spiral_clockwise", CharacterSort.SPIRAL_CLOCKWISE),
        ("spiral_clockwise_double", CharacterSort.SPIRAL_CLOCKWISE_DOUBLE),
        ("spiral_clockwise_quad", CharacterSort.SPIRAL_CLOCKWISE_QUAD),
        ("spiral_counter_clockwise", CharacterSort.SPIRAL_COUNTER_CLOCKWISE),
        ("spiral_counter_clockwise_double", CharacterSort.SPIRAL_COUNTER_CLOCKWISE_DOUBLE),
        ("spiral_counter_clockwise_quad", CharacterSort.SPIRAL_COUNTER_CLOCKWISE_QUAD),
    ],
)
def test_spiral_sort_cli_keys(key: str, sort: CharacterSort) -> None:
    """Spiral keys put direction before the optional arm count and separate counter_clockwise."""
    assert CharacterSortArg.type_parser(key) is sort
    assert key in CharacterSortArg.COMPLETION_CHOICES
