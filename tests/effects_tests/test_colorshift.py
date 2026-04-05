import pytest

from terminaltexteffects.effects import effect_colorshift
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color


def _make_terminal_config(existing_color_handling: str) -> TerminalConfig:
    terminal_config = TerminalConfig._build_config()
    terminal_config.frame_rate = 0
    terminal_config.existing_color_handling = existing_color_handling
    return terminal_config


@pytest.mark.parametrize(
    "input_data",
    ["empty", "single_char", "single_column", "single_row", "medium", "tabs"],
    indirect=True,
)
def test_colorshift_effect_all_inputs(input_data, terminal_config_default_no_framerate) -> None:
    effect = effect_colorshift.ColorShift(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_colorshift_effect_terminal_color_options(input_data, terminal_config_with_color_options) -> None:
    effect = effect_colorshift.ColorShift(input_data)
    effect.terminal_config = terminal_config_with_color_options
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("input_data", ["medium"], indirect=True)
def test_colorshift_final_gradient(
    terminal_config_default_no_framerate,
    input_data,
    gradient_direction,
    gradient_steps,
    gradient_stops,
) -> None:
    effect = effect_colorshift.ColorShift(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.final_gradient_direction = gradient_direction
    effect.effect_config.final_gradient_steps = gradient_steps
    effect.effect_config.final_gradient_stops = gradient_stops
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


@pytest.mark.parametrize("no_loop", [True, False])
@pytest.mark.parametrize("no_travel", [True, False])
@pytest.mark.parametrize("reverse_travel_direction", [True, False])
@pytest.mark.parametrize("cycles", [1, 3])
@pytest.mark.parametrize("skip_final_gradient", [True, False])
@pytest.mark.parametrize("input_data", ["single_char", "medium"], indirect=True)
def test_colorshift_args(
    input_data,
    no_loop,
    no_travel,
    reverse_travel_direction,
    cycles,
    terminal_config_default_no_framerate,
    skip_final_gradient,
    gradient_direction,
    gradient_stops,
    gradient_steps,
    gradient_frames,
) -> None:
    effect = effect_colorshift.ColorShift(input_data)
    effect.terminal_config = terminal_config_default_no_framerate
    effect.effect_config.gradient_stops = gradient_stops
    effect.effect_config.gradient_steps = gradient_steps
    effect.effect_config.gradient_frames = gradient_frames
    effect.effect_config.no_loop = no_loop
    effect.effect_config.no_travel = no_travel
    effect.effect_config.travel_direction = gradient_direction
    effect.effect_config.reverse_travel_direction = reverse_travel_direction
    effect.effect_config.cycles = cycles
    effect.effect_config.skip_final_gradient = skip_final_gradient
    with effect.terminal_output() as terminal:
        for frame in effect:
            terminal.print(frame)


def test_colorshift_dynamic_without_preexisting_colors_has_uncolored_final_frame() -> None:
    effect = effect_colorshift.ColorShift("A")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["final_gradient"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_colorshift.ColorPair()
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code is None


def test_colorshift_dynamic_with_preexisting_fg_uses_input_fg_color() -> None:
    effect = effect_colorshift.ColorShift("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["final_gradient"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_colorshift.ColorPair(fg=Color(196))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code is None


def test_colorshift_dynamic_with_preexisting_fg_and_bg_uses_input_colors() -> None:
    effect = effect_colorshift.ColorShift("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["final_gradient"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_colorshift.ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_colorshift_dynamic_with_preexisting_bg_only_uses_input_bg_color() -> None:
    effect = effect_colorshift.ColorShift("\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("dynamic")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["final_gradient"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_colorshift.ColorPair(bg=Color(106))
    assert final_frame._fg_color_code is None
    assert final_frame._bg_color_code == Color(106).rgb_color


def test_colorshift_ignore_with_preexisting_colors_uses_effect_gradient() -> None:
    effect = effect_colorshift.ColorShift("\x1b[38;5;196mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("ignore")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["final_gradient"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_colorshift.ColorPair(fg=iterator.character_final_color_map[character])
    assert final_frame._fg_color_code == iterator.character_final_color_map[character].rgb_color
    assert final_frame._bg_color_code is None


def test_colorshift_always_with_preexisting_colors_uses_input_colors() -> None:
    effect = effect_colorshift.ColorShift("\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m")
    effect.terminal_config = _make_terminal_config("always")

    iterator = iter(effect)
    character = iterator.terminal.get_characters()[0]
    final_scene = character.animation.scenes["final_gradient"]
    final_frame = final_scene.frames[-1].character_visual

    assert final_frame.symbol == "A"
    assert final_frame.colors == effect_colorshift.ColorPair(fg=Color(196), bg=Color(106))
    assert final_frame._fg_color_code == Color(196).rgb_color
    assert final_frame._bg_color_code == Color(106).rgb_color
