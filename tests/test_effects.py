"""Smoke and visual tests for every bundled effect."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import pytest

from terminaltexteffects.effects import effect_colorshift, effect_matrix, effect_thunderstorm

if TYPE_CHECKING:
    from terminaltexteffects.engine.base_effect import BaseEffect
    from terminaltexteffects.engine.terminal import TerminalConfig

TEST_INPUT_DIR = Path(__file__).parent / "testinput"
MIXED_COLOR_SEQUENCE_INPUT = TEST_INPUT_DIR / "mixed_color_sequence_test.txt"
MIXED_LAYOUT_STYLE_SEQUENCE_INPUT = TEST_INPUT_DIR / "mixed_layout_style_sequence_test.txt"


def _shorten_visual_effect(effect_instance: BaseEffect[Any]) -> None:
    """Shorten long-running visual effect configurations."""
    if isinstance(effect_instance, effect_matrix.Matrix):
        effect_instance.effect_config.rain_time = 5
    elif isinstance(effect_instance, effect_thunderstorm.Thunderstorm):
        effect_instance.effect_config.storm_time = 1
    elif isinstance(effect_instance, effect_colorshift.ColorShift):
        effect_instance.effect_config.cycles = 2


def _print_visual_test_parameters(test_name: str, **parameters: str) -> None:
    """Print a visible separator naming the visual test parameters."""
    formatted_parameters = ", ".join(f"{name}={value}" for name, value in parameters.items())
    print(f"\n=== {test_name}: {formatted_parameters} ===")


@pytest.mark.smoke
@pytest.mark.effects
@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs", "color_sequences"],
    indirect=True,
)
def test_effect(
    effect: type[BaseEffect[Any]],
    input_data: str,
    terminal_config_default_no_framerate: TerminalConfig,
) -> None:
    """Test every effect against representative terminal inputs."""
    effect_instance = effect(input_data)
    # customize some effect configs to shorten testing time
    if isinstance(effect_instance, effect_matrix.Matrix):
        effect_instance.effect_config.rain_time = 1
    elif isinstance(effect_instance, effect_thunderstorm.Thunderstorm):
        effect_instance.effect_config.storm_time = 1
    effect_instance.terminal_config = terminal_config_default_no_framerate

    with effect_instance.terminal_output() as terminal:
        for frame in effect_instance:
            terminal.print(frame)


@pytest.mark.smoke
@pytest.mark.effects
@pytest.mark.parametrize("input_data", ["medium", "color_sequences"], indirect=True)
@pytest.mark.parametrize("existing_color_handling", ["always", "dynamic", "ignore"])
def test_effect_color_sequence_handling(
    effect: type[BaseEffect[Any]],
    input_data: str,
    terminal_config_default_no_framerate: TerminalConfig,
    existing_color_handling: Literal["always", "dynamic", "ignore"],
) -> None:
    """Test each color handling mode against plain and ANSI-colored inputs."""
    effect_instance = effect(input_data)
    if isinstance(effect_instance, effect_matrix.Matrix):
        effect_instance.effect_config.rain_time = 1
    elif isinstance(effect_instance, effect_thunderstorm.Thunderstorm):
        effect_instance.effect_config.storm_time = 1
    effect_instance.terminal_config = terminal_config_default_no_framerate
    effect_instance.terminal_config.existing_color_handling = existing_color_handling

    with effect_instance.terminal_output() as terminal:
        for frame in effect_instance:
            terminal.print(frame)


@pytest.mark.visual
@pytest.mark.parametrize("input_data", ["large"], indirect=True)
def test_effect_visual(effect: type[BaseEffect[Any]], input_data: str) -> None:
    """Render a larger visual sample for each effect."""
    effect_instance = effect(input_data)
    _shorten_visual_effect(effect_instance)
    _print_visual_test_parameters(
        "test_effect_visual",
        effect=effect.__name__,
        input="large",
    )
    with effect_instance.terminal_output() as terminal:
        for frame in effect_instance:
            terminal.print(frame)


@pytest.mark.visual
@pytest.mark.manual
@pytest.mark.parametrize(
    "sequence_input_path",
    [
        pytest.param(MIXED_COLOR_SEQUENCE_INPUT, id="mixed-color"),
        pytest.param(MIXED_LAYOUT_STYLE_SEQUENCE_INPUT, id="mixed-layout-style"),
    ],
)
@pytest.mark.parametrize("existing_color_handling", ["dynamic", "always", "ignore"])
def test_effect_sequence_visual(
    effect: type[BaseEffect[Any]],
    sequence_input_path: Path,
    existing_color_handling: Literal["dynamic", "always", "ignore"],
    terminal_config_default_no_framerate: TerminalConfig,
) -> None:
    """Render each effect with visual sequence fixtures and color handling modes."""
    effect_instance = effect(sequence_input_path.read_text(encoding="utf-8"))
    _shorten_visual_effect(effect_instance)
    effect_instance.terminal_config = terminal_config_default_no_framerate
    effect_instance.terminal_config.existing_color_handling = existing_color_handling
    _print_visual_test_parameters(
        "test_effect_sequence_visual",
        effect=effect.__name__,
        input=sequence_input_path.stem,
        existing_color_handling=existing_color_handling,
    )
    with effect_instance.terminal_output() as terminal:
        for frame in effect_instance:
            terminal.print(frame)


@pytest.mark.skip
@pytest.mark.manual
@pytest.mark.parametrize("input_data", ["canvas"], indirect=True)
def test_canvas_anchoring_large_small_canvas(
    input_data: str,
    effect: type[BaseEffect[Any]],
    terminal_config_with_anchoring: TerminalConfig,
) -> None:
    """Render each effect with manual canvas and text anchoring options."""
    effect_instance = effect(input_data)
    effect_instance.terminal_config = terminal_config_with_anchoring
    with effect_instance.terminal_output() as terminal:
        for frame in effect_instance:
            terminal.print(frame)
