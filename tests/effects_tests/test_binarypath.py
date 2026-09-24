"""Tests for the BinaryPath effect and its configuration surface."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import pytest

from terminaltexteffects.__main__ import build_parser
from terminaltexteffects.effects import effect_binarypath
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color

if TYPE_CHECKING:
    from terminaltexteffects import Gradient


def _make_terminal_config(
    existing_color_handling: Literal["always", "dynamic", "ignore"],
) -> TerminalConfig:
    terminal_config = TerminalConfig._build_config()
    terminal_config.frame_rate = 0
    terminal_config.existing_color_handling = existing_color_handling
    return terminal_config


@pytest.mark.parametrize(
    "input_data",
    ["single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_binarypath_effect(input_data: str, terminal_config_default_no_framerate: TerminalConfig) -> None:
    """Test the BinaryPath effect against a variety of representative inputs."""
    effect = effect_binarypath.BinaryPath(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_binarypath_effect_terminal_color_options(
    input_data: str,
    terminal_config_with_color_options: TerminalConfig,
) -> None:
    """Test BinaryPath output when terminal color toggles change."""
    effect = effect_binarypath.BinaryPath(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_binarypath_iterator_does_not_retain_build_only_state() -> None:
    """Verify build-only color maps and the unused pending queue are not retained."""
    iterator = iter(effect_binarypath.BinaryPath("A"))

    assert not hasattr(iterator, "character_final_color_map")
    assert not hasattr(iterator, "pending_chars")


def test_binarypath_routes_have_no_zero_distance_or_diagonal_segments() -> None:
    """Verify generated routes move through distinct, axis-aligned waypoints to the input coordinate."""
    iterator = effect_binarypath.BinaryPathIterator(effect_binarypath.BinaryPath("A"))
    binary_representation = iterator.pending_binary_representations[0]
    binary_character = binary_representation.binary_characters[0]
    path = binary_character.motion.active_path

    assert path is not None
    assert path.origin_segment is not None
    assert path.origin_segment.start.coord == binary_character.motion.current_coord
    assert path.origin_segment.start.coord != path.origin_segment.end.coord
    assert path.waypoints[0].coord != path.origin_segment.start.coord
    assert sum(waypoint.coord == binary_representation.input_coord for waypoint in path.waypoints) == 1
    assert path.waypoints[-1].coord == binary_representation.input_coord
    for segment in path.segments:
        assert segment.start.coord != segment.end.coord
        assert (
            segment.start.coord.column == segment.end.coord.column
            or segment.start.coord.row == segment.end.coord.row
        )


def test_binarypath_completes_with_very_high_movement_speed() -> None:
    """Verify short paths still complete when movement speed exceeds their length."""
    effect = effect_binarypath.BinaryPath("A")
    effect.effect_config.movement_speed = 10_000

    iterator = effect_binarypath.BinaryPathIterator(effect)
    frames = list(iterator)

    assert frames
    assert iterator.complete


def test_binarypath_binary_characters_use_static_colored_appearance() -> None:
    """Verify binary characters keep their configured color without allocating animation scenes."""
    effect = effect_binarypath.BinaryPath("A")
    iterator = effect_binarypath.BinaryPathIterator(effect)
    binary_representation = iterator.pending_binary_representations[0]

    for character, symbol in zip(binary_representation.binary_characters, format(ord("A"), "08b"), strict=True):
        visual = character.animation.current_character_visual
        assert visual.symbol == symbol
        assert visual.colors is not None
        assert visual.colors.fg in effect.effect_config.binary_colors
        assert character.animation.scenes == {}
        assert character.motion.active_path is not None


def test_binarypath_cli_help_describes_gradient_and_group_fraction(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify the CLI describes the spatial gradient and the zero-value group minimum."""
    parser, _ = build_parser(include_user_effects=False)

    with pytest.raises(SystemExit) as exit_info:
        parser.parse_args(["binarypath", "--help"])

    assert exit_info.value.code == 0
    help_text = " ".join(capsys.readouterr().out.split())
    assert "color-transition steps used for the spatial final-color gradient" in help_text
    assert "Maximum fraction of binary groups active at once" in help_text
    assert "0 still activates one group" in help_text


def test_binarypath_zero_active_group_fraction_still_runs_one_group() -> None:
    """Verify zero parses through the CLI and the iterator keeps its one-group minimum."""
    parser, _ = build_parser(include_user_effects=False)
    arguments = parser.parse_args(["binarypath", "--active-binary-groups", "0"])
    effect = effect_binarypath.BinaryPath("A")
    effect.effect_config.active_binary_groups = arguments.active_binary_groups
    iterator = effect_binarypath.BinaryPathIterator(effect)

    assert iterator.config.active_binary_groups == 0
    assert iterator.max_active_binary_groups == 1


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_binarypath_final_gradient(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    gradient_direction: Gradient.Direction,
    gradient_steps: tuple[int, ...],
    gradient_stops: tuple[Color, ...],
) -> None:
    """Verify the BinaryPath effect respects final gradient settings."""
    effect = effect_binarypath.BinaryPath(input_data)
    effect.effect_config.final_gradient_stops = gradient_stops
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("binary_colors", [(Color("#ffffff"),), (Color("#f0f0f0"), Color("#0f0f0f"))])
@pytest.mark.parametrize("movement_speed", [0.5, 1, 4])
@pytest.mark.parametrize("active_binary_groups", [0.0001, 0.5, 1.0])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_binarypath_args(
    terminal_config_default_no_framerate: TerminalConfig,
    input_data: str,
    binary_colors: tuple[Color, ...],
    movement_speed: float,
    active_binary_groups: float,
) -> None:
    """Ensure BinaryPath accepts and renders with various configuration arguments."""
    effect = effect_binarypath.BinaryPath(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.binary_colors = binary_colors
    effect.effect_config.movement_speed = movement_speed
    effect.effect_config.active_binary_groups = active_binary_groups
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_binarypath_dynamic_without_preexisting_colors_has_uncolored_final_frame() -> None:
    """Verify dynamic mode leaves uncolored input uncolored at the final settle state."""
    effect = effect_binarypath.BinaryPath("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["brighten_scn"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_binarypath.tte.ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_binarypath_dynamic_with_preexisting_fg_uses_input_fg_color() -> None:
    """Verify dynamic mode restores a parsed foreground color in the final settle state."""
    effect = effect_binarypath.BinaryPath("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["brighten_scn"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_binarypath.tte.ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_binarypath_dynamic_with_preexisting_fg_and_bg_uses_input_colors() -> None:
    """Verify dynamic mode restores parsed foreground and background colors together."""
    effect = effect_binarypath.BinaryPath("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["brighten_scn"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_binarypath.tte.ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_binarypath_dynamic_with_preexisting_bg_only_uses_input_bg_color() -> None:
    """Verify dynamic mode restores a parsed background color without inventing a foreground."""
    effect = effect_binarypath.BinaryPath("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["brighten_scn"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_binarypath.tte.ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color
