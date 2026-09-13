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
    assert terminal._inner_fill_characters == []
    assert terminal._next_character_id == 17

    fill_characters = terminal.get_characters(input_chars=False, inner_fill_chars=True)

    assert len(fill_characters) == 7
    assert [character.character_id for character in terminal._inner_fill_characters] == list(range(10, 17))


def test_terminal_defers_neighbor_graph_until_character_neighbors_are_read() -> None:
    """Direct neighbor access should transparently prepare the complete graph once."""
    config = TerminalConfig._build_config()
    config.ignore_terminal_dimensions = True
    config.canvas_width = 3
    config.canvas_height = 2
    terminal = Terminal(input_data="A", config=config)
    input_character = terminal.get_characters()[0]

    assert input_character._neighbors is None
    assert terminal._outer_fill_characters == []
    assert not terminal._character_neighbors_initialized

    east_neighbor = input_character.neighbors["east"]

    assert east_neighbor is terminal.get_character_by_input_coord(Coord(2, 1))
    assert terminal._character_neighbors_initialized
    assert len(terminal._outer_fill_characters) == 5


def test_terminal_creates_one_requested_fill_with_reserved_id() -> None:
    """Coordinate lookup should materialize one fill without changing helper ID ordering."""
    config = TerminalConfig._build_config()
    config.ignore_terminal_dimensions = True
    config.canvas_width = 3
    config.canvas_height = 2
    terminal = Terminal(input_data="A", config=config)
    helper = terminal.add_character("B", Coord(2, 1))

    fill_character = terminal.get_character_by_input_coord(Coord(2, 1))

    assert fill_character is not None
    assert fill_character.is_fill_character
    assert fill_character.character_id == 1
    assert helper.character_id == 6
    assert terminal._inner_fill_characters == []
    assert terminal._outer_fill_characters == [fill_character]


def test_public_character_mapping_materializes_all_fill_characters() -> None:
    """The public coordinate mapping should retain its complete-canvas contract."""
    config = TerminalConfig._build_config()
    config.ignore_terminal_dimensions = True
    config.canvas_width = 3
    config.canvas_height = 2
    terminal = Terminal(input_data="A", config=config)

    character_mapping = terminal.character_by_input_coord

    assert len(character_mapping) == 6
    assert len(terminal._inner_fill_characters) == 0
    assert len(terminal._outer_fill_characters) == 5
    assert terminal._fill_characters_materialized


def test_prepare_character_graph_materializes_once() -> None:
    """Graph preparation should create all fills and stable cardinal neighbor mappings once."""
    config = TerminalConfig._build_config()
    config.ignore_terminal_dimensions = True
    config.canvas_width = 2
    config.canvas_height = 2
    terminal = Terminal(input_data="A", config=config)
    input_character = terminal.get_characters()[0]

    terminal.prepare_character_graph()
    first_fill_characters = terminal.get_characters(input_chars=False, outer_fill_chars=True)
    terminal.prepare_character_graph()

    assert len(first_fill_characters) == 3
    assert input_character.neighbors["east"] is terminal.get_character_by_input_coord(Coord(2, 1))
    assert input_character.neighbors["north"] is terminal.get_character_by_input_coord(Coord(1, 2))
    assert terminal.get_characters(input_chars=False, outer_fill_chars=True) == first_fill_characters


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
