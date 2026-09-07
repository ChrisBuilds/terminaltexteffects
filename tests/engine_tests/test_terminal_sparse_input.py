"""Tests for sparse terminal input preprocessing."""

from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.utils.geometry import Coord


def test_terminal_preprocessing_keeps_unstyled_gaps_sparse_and_preserves_ids() -> None:
    """Unstyled gaps retain layout and historical ID progression without input objects."""
    config = TerminalConfig._build_config()
    config.ignore_terminal_dimensions = True

    terminal = Terminal(input_data="A   B\nC", config=config)

    assert [len(line) for line in terminal._preprocessed_character_lines] == [2, 1]
    assert terminal._preprocessed_line_widths == [5, 1]
    assert [character.character_id for character in terminal.get_characters()] == [0, 4, 5]
    assert [character.input_coord for character in terminal.get_characters()] == [
        Coord(1, 2),
        Coord(5, 2),
        Coord(1, 1),
    ]
    assert len(terminal._inner_fill_characters) == 7
    assert terminal._inner_fill_characters[0].character_id == 10
    assert terminal._next_character_id == 17


def test_terminal_sparse_tab_retains_following_character_column() -> None:
    """Expanded unstyled tab cells should not shift the following input character."""
    config = TerminalConfig._build_config()
    config.ignore_terminal_dimensions = True

    terminal = Terminal(input_data="A\tB", config=config)

    assert [len(line) for line in terminal._preprocessed_character_lines] == [2]
    assert terminal._preprocessed_line_widths == [5]
    assert [character.character_id for character in terminal.get_characters()] == [0, 4]
    assert [character.input_coord for character in terminal.get_characters()] == [Coord(1, 1), Coord(5, 1)]


def test_terminal_sparse_gap_wraps_by_logical_columns() -> None:
    """Wrapping should retain empty chunks and the post-gap character position."""
    config = TerminalConfig._build_config()
    config.canvas_width = 2
    config.wrap_text = True
    config.ignore_terminal_dimensions = True

    terminal = Terminal(input_data="A   B", config=config)

    assert len(terminal._wrapped_character_lines or []) == 3
    assert terminal._wrapped_character_line_widths == [2, 2, 1]
    assert [character.input_coord for character in terminal.get_characters()] == [Coord(1, 3), Coord(1, 1)]
    assert (terminal.canvas.text_width, terminal.canvas.text_height) == (1, 3)
