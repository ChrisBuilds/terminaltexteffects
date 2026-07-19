"""Focused tests for the Fireflies effect."""

from __future__ import annotations

import importlib
import importlib.util
import random
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

import pytest

from terminaltexteffects import __main__
from terminaltexteffects.effects import effect_fireflies
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.graphics import Color, ColorPair, Gradient

if TYPE_CHECKING:
    from terminaltexteffects.engine.motion import Path as MotionPath


def _make_iterator(
    input_data: str,
    *,
    seed: int = 7,
    auxiliary_count: int = 0,
    wander_cycles: int = 3,
    movement_speed: float = 0.18,
    existing_color_handling: Literal["always", "dynamic", "ignore"] = "ignore",
) -> effect_fireflies.FirefliesIterator:
    """Build a deterministic Fireflies iterator without terminal frame limiting."""
    random.seed(seed)
    effect = effect_fireflies.Fireflies(input_data)
    effect.effect_config.auxiliary_count = auxiliary_count
    effect.effect_config.wander_cycles = wander_cycles
    effect.effect_config.movement_speed = movement_speed
    terminal_config = TerminalConfig._build_config()
    terminal_config.frame_rate = 0
    terminal_config.ignore_terminal_dimensions = True
    terminal_config.existing_color_handling = existing_color_handling
    effect.terminal_config = terminal_config
    return cast("effect_fireflies.FirefliesIterator", iter(effect))


def _run_to_completion(
    iterator: effect_fireflies.FirefliesIterator,
    *,
    max_frames: int = 3000,
) -> tuple[list[str], set[effect_fireflies.FireflyState]]:
    """Consume an iterator with a guard and record all primary states observed."""
    frames: list[str] = []
    observed_states = {firefly.state for firefly in iterator.fireflies}
    for _ in range(max_frames):
        try:
            frames.append(next(iterator))
        except StopIteration:
            return frames, observed_states
        observed_states.update(firefly.state for firefly in iterator.fireflies)
    pytest.fail(f"Fireflies did not terminate within {max_frames} frames")


def _path_signature(path: MotionPath) -> tuple[object, ...]:
    """Serialize observable path planning data for deterministic comparisons."""
    return (
        path.path_id,
        path.speed,
        tuple((waypoint.coord, waypoint.bezier_control) for waypoint in path.waypoints),
    )


def test_fireflies_module_and_public_export() -> None:
    """Fireflies should be available through its module and the public effects package."""
    module_spec = importlib.util.find_spec("terminaltexteffects.effects.effect_fireflies")

    assert module_spec is not None

    fireflies_module = importlib.import_module("terminaltexteffects.effects.effect_fireflies")
    effects_package = importlib.import_module("terminaltexteffects.effects")
    command, effect_class, config_class = fireflies_module.get_effect_resources()

    assert command == "fireflies"
    assert effect_class is fireflies_module.Fireflies
    assert config_class is fireflies_module.FirefliesConfig
    assert effects_package.Fireflies is fireflies_module.Fireflies


def test_fireflies_cli_discovery_and_defaults(capsys: pytest.CaptureFixture[str]) -> None:
    """CLI discovery should expose Fireflies and its expressive default configuration."""
    parser, effect_resource_map = __main__.build_parser()

    assert "fireflies" in effect_resource_map
    assert "fireflies" in parser.format_help()

    parsed_args = parser.parse_args(["fireflies"])
    config_class = effect_resource_map["fireflies"][1]
    config = config_class._build_config(parsed_args)

    assert config.firefly_colors == (Color("#6b5c20"), Color("#d4a72c"), Color("#fff2a1"))
    assert config.firefly_symbols == (".", "*", "o", "*")
    assert config.movement_speed == 0.18
    assert config.wander_cycles == 3
    assert config.auxiliary_count == 6
    assert config.final_gradient_stops == (Color("#3f4f24"), Color("#d6a928"), Color("#ffe680"))
    assert config.final_gradient_steps == 12
    assert config.final_gradient_direction is Gradient.Direction.HORIZONTAL

    with pytest.raises(SystemExit, match="0"):
        parser.parse_args(["fireflies", "--help"])
    fireflies_help = capsys.readouterr().out
    assert "--firefly-colors" in fireflies_help
    assert "--auxiliary-count" in fireflies_help


@pytest.mark.parametrize(
    "arguments",
    [
        ["--movement-speed", "0"],
        ["--wander-cycles", "0"],
        ["--auxiliary-count", "-1"],
        ["--firefly-symbols", "too-wide"],
        ["--firefly-colors", "not-a-color"],
    ],
)
def test_fireflies_cli_rejects_invalid_configuration(
    arguments: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Every Fireflies option should use the repository's standard validators."""
    parser, _ = __main__.build_parser()

    with pytest.raises(SystemExit, match="2"):
        parser.parse_args(["fireflies", *arguments])

    assert "unrecognized arguments" not in capsys.readouterr().err


def test_firefly_state_creation_and_bounded_paths() -> None:
    """Every input character should receive a bounded, in-canvas firefly plan."""
    iterator = _make_iterator("ABCDE\nFGHIJ\nKLMNO", wander_cycles=3)

    assert len(iterator.fireflies) == len(iterator.terminal.get_characters())
    assert iterator.clusters

    for firefly in iterator.fireflies:
        character = firefly.character
        start = firefly.start_coord
        canvas = iterator.terminal.canvas

        assert firefly.state is effect_fireflies.FireflyState.DORMANT
        assert firefly.target_coord == character.input_coord
        assert character.motion.current_coord == start
        assert canvas.coord_is_in_canvas(start)
        assert start.column in (canvas.left, canvas.right) or start.row in (canvas.bottom, canvas.top)
        assert not character.is_visible
        assert firefly.arrival_radius >= 1
        assert firefly.attraction_strength == 0

        assert "enter" in character.motion.paths
        assert "wander" in character.motion.paths
        assert "approach" in character.motion.paths
        assert len(character.motion.paths["wander"].waypoints) <= iterator.config.wander_cycles
        assert character.motion.paths["approach"].waypoints[-1].coord == character.input_coord
        assert all(not path.loop for path in character.motion.paths.values())

        total_waypoints = 0
        for path in character.motion.paths.values():
            total_waypoints += len(path.waypoints)
            for waypoint in path.waypoints:
                assert canvas.coord_is_in_canvas(waypoint.coord)
                assert all(canvas.coord_is_in_canvas(control) for control in waypoint.bezier_control or ())
        assert total_waypoints <= iterator.config.wander_cycles + 5


def test_fireflies_receive_varied_blink_motion_and_cluster_schedules() -> None:
    """Blink and motion schedules should vary while spatial groups remain bounded."""
    iterator = _make_iterator("ABCDEFGHIJKLMNOP\nQRSTUVWXYZabcdef")

    blink_signatures = [firefly.blink_signature for firefly in iterator.fireflies]
    motion_signatures = [
        tuple(_path_signature(path) for path in firefly.character.motion.paths.values())
        for firefly in iterator.fireflies
    ]

    assert len(set(blink_signatures[:8])) == 8
    assert len(set(motion_signatures)) > 1
    assert len({firefly.activation_frame for firefly in iterator.fireflies}) > 1
    assert len({firefly.release_frame for firefly in iterator.fireflies}) > 1

    for firefly in iterator.fireflies:
        blink_scene = firefly.character.animation.query_scene("blink")
        assert blink_scene.is_looping
        assert len({frame.character_visual.colors.fg_color for frame in blink_scene.frames}) >= 3
        assert all(frame.character_visual.symbol in iterator.config.firefly_symbols for frame in blink_scene.frames)

    for cluster in iterator.clusters.values():
        columns = [firefly.target_coord.column for firefly in cluster]
        rows = [firefly.target_coord.row for firefly in cluster]
        assert max(columns) - min(columns) <= 3
        assert max(rows) - min(rows) <= 1
        assert all(firefly.group_leader is cluster[0] for firefly in cluster[1:])


def test_firefly_planning_is_deterministic_under_repository_seed_convention() -> None:
    """Resetting module-level random should reproduce all planned schedules and paths."""

    def serialize(iterator: effect_fireflies.FirefliesIterator) -> tuple[object, ...]:
        return tuple(
            (
                firefly.start_coord,
                firefly.cluster_id,
                firefly.activation_frame,
                firefly.release_frame,
                firefly.blink_signature,
                tuple(_path_signature(path) for path in firefly.character.motion.paths.values()),
            )
            for firefly in iterator.fireflies
        )

    first = serialize(_make_iterator("DETERMINISTIC\nFIREFLIES", seed=41))
    second = serialize(_make_iterator("DETERMINISTIC\nFIREFLIES", seed=41))

    assert first == second


def test_fireflies_progress_through_living_states_and_restore_exact_text() -> None:
    """Primary fireflies should wander, gather, land, pulse, and finish exactly."""
    iterator = _make_iterator("ABCDE\nFGHIJ", seed=17, wander_cycles=1, movement_speed=1.0)

    frames, observed_states = _run_to_completion(iterator)

    assert frames
    assert {
        effect_fireflies.FireflyState.DORMANT,
        effect_fireflies.FireflyState.ENTERING,
        effect_fireflies.FireflyState.WANDERING,
        effect_fireflies.FireflyState.GATHERING,
        effect_fireflies.FireflyState.APPROACHING,
        effect_fireflies.FireflyState.ILLUMINATING,
        effect_fireflies.FireflyState.SETTLED,
    } <= observed_states
    assert effect_fireflies.FireflyState.ORBITING in observed_states
    assert iterator.phase is effect_fireflies.FirefliesPhase.COMPLETE
    assert iterator.final_frame_shown

    for firefly in iterator.fireflies:
        character = firefly.character
        assert firefly.state is effect_fireflies.FireflyState.SETTLED
        assert firefly.settled_frame is not None
        assert character.motion.current_coord == character.input_coord
        assert character.animation.current_character_visual.symbol == character.input_symbol
        assert character.animation.current_character_visual.colors == iterator.character_final_color_map[character]
        assert character.layer == 0
        assert character.is_visible
        assert character.motion.active_path is None
        assert character.animation.active_scene is None


def test_arrivals_and_final_pulse_are_staggered_in_groups() -> None:
    """Settlements should be uneven and the final warm pulse should travel in groups."""
    iterator = _make_iterator("ABCDEFGHIJKLMNOP\nQRSTUVWXYZabcdef", seed=23, wander_cycles=1, movement_speed=1.0)

    _run_to_completion(iterator)

    settled_frames = [firefly.settled_frame for firefly in iterator.fireflies]
    assert None not in settled_frames
    assert len(set(settled_frames)) > 3
    assert len(iterator.pulse_activation_frames) > 1
    assert list(iterator.pulse_activation_frames) == sorted(iterator.pulse_activation_frames)
    assert len(set(iterator.pulse_activation_frames)) > 1


def test_auxiliary_fireflies_depart_reuse_as_halos_and_cleanup() -> None:
    """Atmospheric helpers should depart, support bounded halo reuse, and leave no artifacts."""
    iterator = _make_iterator(
        "ABCDEFGHIJKLMNOP\nQRSTUVWXYZabcdef\nghijklmnopqrstuv",
        seed=31,
        auxiliary_count=4,
        wander_cycles=1,
        movement_speed=1.0,
    )

    assert len(iterator.auxiliary_pool) == 4
    assert all(not particle.is_visible for particle in iterator.auxiliary_pool.particles)
    assert len(iterator.auxiliary_pool.available) == len(iterator.auxiliary_pool)

    _run_to_completion(iterator)

    assert iterator.auxiliary_departure_frame is not None
    assert iterator.halo_emissions > 0
    assert len(iterator.auxiliary_pool.available) == len(iterator.auxiliary_pool)
    assert all(not particle.is_visible for particle in iterator.auxiliary_pool.particles)
    assert all(particle not in iterator.active_characters for particle in iterator.auxiliary_pool.particles)
    assert all(particle.animation.active_scene is None for particle in iterator.auxiliary_pool.particles)
    assert all(particle.motion.active_path is None for particle in iterator.auxiliary_pool.particles)


@pytest.mark.parametrize(
    "input_data",
    [
        "",
        "A",
        "ABCDE",
        "A\nB\nC\nD",
        "A   D\n\n  G",
        "ABCD\nEFGH\nIJKL",
    ],
)
def test_fireflies_terminates_and_restores_representative_inputs(input_data: str) -> None:
    """Empty, tiny, sparse, one-dimensional, and multiline inputs should finish exactly."""
    iterator = _make_iterator(input_data, seed=43, wander_cycles=1, movement_speed=1.0)
    original = {
        character.character_id: (character.input_symbol, character.input_coord)
        for character in iterator.terminal.get_characters()
    }

    _run_to_completion(iterator)

    assert iterator.phase is effect_fireflies.FirefliesPhase.COMPLETE
    for character in iterator.terminal.get_characters():
        expected_symbol, expected_coord = original[character.character_id]
        assert character.animation.current_character_visual.symbol == expected_symbol
        assert character.motion.current_coord == expected_coord


def test_fireflies_handles_whitespace_only_python_input() -> None:
    """Whitespace-only API input should render one quiet frame and terminate without particles."""
    iterator = _make_iterator("   \n ", seed=47, auxiliary_count=6, wander_cycles=1, movement_speed=1.0)

    frames, _ = _run_to_completion(iterator, max_frames=10)

    assert frames == [" "]
    assert iterator.fireflies == []
    assert len(iterator.auxiliary_pool) == 0
    assert iterator.phase is effect_fireflies.FirefliesPhase.COMPLETE


@pytest.mark.parametrize(
    ("input_data", "mode", "expected_colors"),
    [
        ("\x1b[38;5;196mA\x1b[0m", "dynamic", ColorPair(fg=Color(196))),
        ("\x1b[48;5;106m \x1b[0m", "dynamic", ColorPair(bg=Color(106))),
        (
            "\x1b[38;5;196m\x1b[48;5;106mA\x1b[0m",
            "always",
            ColorPair(fg=Color(196), bg=Color(106)),
        ),
    ],
)
def test_fireflies_restores_ansi_input_colors(
    input_data: str,
    mode: Literal["always", "dynamic"],
    expected_colors: ColorPair,
) -> None:
    """Dynamic and always modes should restore parsed fg/bg channels, including colored spaces."""
    iterator = _make_iterator(
        input_data,
        seed=53,
        wander_cycles=1,
        movement_speed=1.0,
        existing_color_handling=mode,
    )

    _run_to_completion(iterator)

    character = iterator.terminal.get_characters()[0]
    assert character.animation.current_character_visual.symbol == character.input_symbol
    assert character.animation.current_character_visual.colors == expected_colors
    assert iterator.character_final_color_map[character] == expected_colors


def test_fireflies_ignore_mode_uses_effect_gradient_for_ansi_input() -> None:
    """Ignore mode should finish with the configured gradient rather than parsed input colors."""
    iterator = _make_iterator(
        "\x1b[38;5;196mA\x1b[0m",
        seed=59,
        wander_cycles=1,
        movement_speed=1.0,
        existing_color_handling="ignore",
    )

    _run_to_completion(iterator)

    character = iterator.terminal.get_characters()[0]
    assert character.animation.current_character_visual.colors == iterator.character_final_color_map[character]
    assert character.animation.current_character_visual.colors != ColorPair(fg=Color(196))


def test_fireflies_representative_cli_execution() -> None:
    """The installed module entry point should render Fireflies successfully with a fixed seed."""
    input_file = Path(__file__).parents[1] / "testinput" / "single_char.txt"

    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "terminaltexteffects",
            "--input-file",
            str(input_file),
            "--frame-rate",
            "0",
            "--seed",
            "7",
            "fireflies",
            "--movement-speed",
            "1",
            "--wander-cycles",
            "1",
            "--auxiliary-count",
            "0",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parents[2],
    )

    assert result.returncode == 0, result.stderr
    assert "a" in result.stdout
