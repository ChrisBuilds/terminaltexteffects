"""Tests for the Snake effect."""

from __future__ import annotations

import importlib
from typing import Literal, cast

import pytest

from terminaltexteffects.effects import effect_snake
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.graphics import Color, ColorPair, Gradient


def _make_terminal_config(
    existing_color_handling: Literal["always", "dynamic", "ignore"] = "ignore",
) -> TerminalConfig:
    """Build a no-frame-rate terminal config for effect tests."""
    terminal_config = TerminalConfig._build_config()
    terminal_config.frame_rate = 0
    terminal_config.existing_color_handling = existing_color_handling
    return terminal_config


def _run_to_completion(
    effect: effect_snake.Snake,
    frame_limit: int = 500,
) -> effect_snake.SnakeIterator:
    """Run an effect to completion with an infinite-iteration guard."""
    iterator = cast("effect_snake.SnakeIterator", iter(effect))
    for _ in range(frame_limit):
        try:
            next(iterator)
        except StopIteration:  # noqa: PERF203
            return iterator
    pytest.fail(f"Snake iterator did not terminate within {frame_limit} frames")


def test_snake_module_exposes_public_effect_resources() -> None:
    """Snake modules expose the standard discovery resources."""
    effect_snake = importlib.import_module("terminaltexteffects.effects.effect_snake")

    assert effect_snake.get_effect_resources() == (
        "snake",
        effect_snake.Snake,
        effect_snake.SnakeConfig,
    )


def test_snake_is_exported_from_effects_package() -> None:
    """Snake is available from the public effects package."""
    effects = importlib.import_module("terminaltexteffects.effects")

    assert effects.Snake.__name__ == "Snake"


def test_snake_config_builds_expected_defaults() -> None:
    """Snake config builds the documented defaults."""
    effect_snake = importlib.import_module("terminaltexteffects.effects.effect_snake")

    config = effect_snake.SnakeConfig._build_config()

    assert config.snake_count == 4
    assert config.snake_colors == (Color("#22c55e"), Color("#84cc16"), Color("#a3e635"))
    assert config.movement_speed == 1.0
    assert config.spawn_delay == 3
    assert config.head_symbol == "●"
    assert config.final_gradient_stops == (Color("#22c55e"), Color("#84cc16"), Color("#fde047"))
    assert config.final_gradient_steps == 12
    assert config.final_gradient_direction is Gradient.Direction.HORIZONTAL


def test_snake_count_clamps_and_assigns_each_target_once() -> None:
    """Effective snake count clamps and every target is uniquely assigned."""
    effect = effect_snake.Snake("ABCDEF")
    effect.effect_config.snake_count = 20
    effect.terminal_config = TerminalConfig._build_config()
    effect.terminal_config.frame_rate = 0

    iterator = cast("effect_snake.SnakeIterator", iter(effect))
    assigned = [character for snake in iterator.snakes for character in snake.carried]

    assert len(iterator.snakes) == 6
    assert len(assigned) == 6
    assert set(assigned) == set(iterator.terminal.get_characters())


def test_snake_targets_follow_a_row_serpentine_route() -> None:
    """Targets follow a coherent alternating row route."""
    effect = effect_snake.Snake("ABC\nDEF")
    effect.effect_config.snake_count = 1

    iterator = cast("effect_snake.SnakeIterator", iter(effect))

    assert "".join(character.input_symbol for character in iterator.snakes[0].carried) == "ABCFED"


def test_snake_head_starts_outside_its_assigned_canvas_edge() -> None:
    """A snake head begins one cell outside its assigned edge."""
    effect = effect_snake.Snake("ABCD")
    effect.effect_config.snake_count = 1

    iterator = cast("effect_snake.SnakeIterator", iter(effect))
    snake = iterator.snakes[0]

    assert snake.entry_edge == "left"
    assert snake.head.motion.current_coord.column == iterator.terminal.canvas.left - 1
    assert snake.head.motion.current_coord.row == snake.carried[0].input_coord.row


def test_snake_orients_each_target_group_toward_its_entry_edge() -> None:
    """Each group starts from the endpoint nearest its entry edge."""
    effect = effect_snake.Snake("ABCDEFGH")
    effect.effect_config.snake_count = 2

    iterator = cast("effect_snake.SnakeIterator", iter(effect))

    assert iterator.snakes[1].entry_edge == "right"
    assert iterator.snakes[1].carried[0].input_symbol == "H"


def test_snake_route_inserts_an_orthogonal_corner() -> None:
    """Routes between offset targets contain only orthogonal segments."""
    iterator = cast("effect_snake.SnakeIterator", iter(effect_snake.Snake("A")))

    waypoints = iterator._orthogonal_waypoints(Coord(1, 1), Coord(4, 3), horizontal_first=True)

    assert waypoints == [Coord(4, 1), Coord(4, 3)]
    assert all(
        start.column == end.column or start.row == end.row for start, end in zip([Coord(1, 1), *waypoints], waypoints)
    )


def test_snake_trail_records_every_grid_cell_crossed_by_the_head() -> None:
    """Head jumps are expanded into every crossed grid coordinate."""
    effect = effect_snake.Snake("ABCD")
    effect.effect_config.snake_count = 1
    iterator = cast("effect_snake.SnakeIterator", iter(effect))
    snake = iterator.snakes[0]
    start = snake.head.motion.current_coord
    snake.head.motion.set_coordinate(Coord(start.column + 3, start.row))

    iterator._update_trail(snake)

    assert list(snake.trail)[:4] == [
        Coord(start.column + 3, start.row),
        Coord(start.column + 2, start.row),
        Coord(start.column + 1, start.row),
        start,
    ]
    assert [character.motion.current_coord for character in snake.carried] == list(snake.trail)[:4]


def test_snake_zero_spawn_delay_activates_multiple_snakes_together() -> None:
    """A zero delay starts multiple snakes in the same frame."""
    effect = effect_snake.Snake("ABCDEFGH")
    effect.effect_config.snake_count = 4
    effect.effect_config.spawn_delay = 0
    iterator = cast("effect_snake.SnakeIterator", iter(effect))

    next(iterator)

    assert all(snake.head.is_visible for snake in iterator.snakes)
    assert all(snake.head.motion.active_path is not None for snake in iterator.snakes)


def test_snake_deposits_every_character_and_cleans_up_heads() -> None:
    """Completion deposits exact input state and hides auxiliary heads."""
    effect = effect_snake.Snake("SNAKE\nGAME!")
    effect.effect_config.snake_count = 3
    effect.effect_config.spawn_delay = 0
    effect.effect_config.movement_speed = 2
    effect.terminal_config = TerminalConfig._build_config()
    effect.terminal_config.frame_rate = 0
    iterator = _run_to_completion(effect)

    assert all(character.is_visible for character in iterator.terminal.get_characters())
    assert all(
        character.motion.current_coord == character.input_coord for character in iterator.terminal.get_characters()
    )
    assert all(
        character.animation.current_character_visual.symbol == character.input_symbol
        for character in iterator.terminal.get_characters()
    )
    assert all(not snake.head.is_visible for snake in iterator.snakes)
    assert iterator.active_characters == set()


def test_snake_body_follows_the_head_around_a_turn() -> None:
    """Body segments retain the head's corner in their trail."""
    effect = effect_snake.Snake("ABCDE")
    effect.effect_config.snake_count = 1
    iterator = cast("effect_snake.SnakeIterator", iter(effect))
    snake = iterator.snakes[0]
    start = snake.head.motion.current_coord
    snake.head.motion.set_coordinate(Coord(start.column + 3, start.row))
    iterator._update_trail(snake)
    snake.head.motion.set_coordinate(Coord(start.column + 3, start.row + 2))

    iterator._update_trail(snake)

    body_coords = [character.motion.current_coord for character in snake.carried]
    assert Coord(start.column + 3, start.row) in body_coords
    assert all(
        abs(first.column - second.column) + abs(first.row - second.row) <= 1
        for first, second in zip(body_coords, body_coords[1:])
    )


def test_snake_whitespace_only_input_emits_one_blank_frame_and_stops() -> None:
    """Whitespace-only input produces a blank finite effect."""
    effect = effect_snake.Snake("   \n  ")
    effect.terminal_config = _make_terminal_config()
    iterator = cast("effect_snake.SnakeIterator", iter(effect))

    assert next(iterator).strip() == ""
    with pytest.raises(StopIteration):
        next(iterator)


def test_snake_dynamic_mode_restores_input_foreground_and_background_colors() -> None:
    """Dynamic mode restores parsed foreground and background colors."""
    effect = effect_snake.Snake("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.effect_config.movement_speed = 2
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = _run_to_completion(effect)
    character = iterator.terminal.get_characters()[0]

    assert character.animation.current_character_visual.colors == ColorPair(fg=Color(196), bg=Color(106))


def test_snake_dynamic_mode_preserves_a_background_colored_space() -> None:
    """Dynamic mode preserves a background-colored input space."""
    effect = effect_snake.Snake("\x1b[48;5;106m \x1b[0m")
    effect.effect_config.movement_speed = 2
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = _run_to_completion(effect)
    character = iterator.terminal.get_characters()[0]

    assert character.input_symbol == " "
    assert character.animation.current_character_visual.colors == ColorPair(bg=Color(106))


def test_snake_ignore_mode_finishes_with_the_configured_gradient_color() -> None:
    """Ignore mode settles into the configured final gradient."""
    effect = effect_snake.Snake("A")
    effect.effect_config.movement_speed = 2
    effect.effect_config.final_gradient_stops = (Color("#ff00ff"),)
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = _run_to_completion(effect)
    character = iterator.terminal.get_characters()[0]

    assert character.animation.current_character_visual.colors == ColorPair(fg=Color("#ff00ff"))


def test_snake_always_mode_finishes_with_input_colors() -> None:
    """Always mode finishes with engine-controlled input colors."""
    effect = effect_snake.Snake("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.effect_config.movement_speed = 2
    effect.terminal_config = _make_terminal_config("always")

    iterator = _run_to_completion(effect)
    character = iterator.terminal.get_characters()[0]

    assert character.animation.current_character_visual.colors == ColorPair(fg=Color(196), bg=Color(106))


def test_snake_empty_input_uses_the_terminal_no_input_convention() -> None:
    """Empty input retains the engine's No Input convention."""
    effect = effect_snake.Snake("")
    effect.effect_config.movement_speed = 4
    effect.effect_config.spawn_delay = 0
    effect.terminal_config = _make_terminal_config()

    iterator = _run_to_completion(effect)

    assert "".join(character.input_symbol for character in iterator.terminal.get_characters()) == "NoInput."


def test_snake_visibly_shrinks_after_depositing_a_character() -> None:
    """A deposited character leaves the carried body shorter."""
    effect = effect_snake.Snake("AB")
    effect.effect_config.snake_count = 1
    effect.effect_config.spawn_delay = 0
    effect.effect_config.movement_speed = 1
    effect.terminal_config = _make_terminal_config()
    iterator = cast("effect_snake.SnakeIterator", iter(effect))
    snake = iterator.snakes[0]

    for _ in range(20):
        next(iterator)
        if len(snake.carried) == 1:
            break

    assert len(snake.carried) == 1
    deposited = iterator.terminal.get_characters()[0]
    assert deposited.motion.current_coord == deposited.input_coord
    assert deposited.layer == 0
    assert snake.head.is_visible


def test_snake_tiny_canvas_clamps_to_the_retained_character() -> None:
    """Tiny canvases animate only the input character retained by Terminal."""
    effect = effect_snake.Snake("AB")
    effect.effect_config.snake_count = 4
    effect.effect_config.movement_speed = 2
    effect.terminal_config = _make_terminal_config()
    effect.terminal_config.canvas_width = 1
    effect.terminal_config.canvas_height = 1

    iterator = _run_to_completion(effect)

    assert len(iterator.snakes) == 1
    assert [character.input_symbol for character in iterator.terminal.get_characters()] == ["A"]
