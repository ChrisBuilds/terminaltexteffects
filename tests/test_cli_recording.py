"""CLI recording and playback without real-time animation waits."""

from __future__ import annotations

import json
import os
import random
import struct
import sys
import zlib
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from terminaltexteffects import __main__
from terminaltexteffects.effects.effect_matrix import Matrix, MatrixConfig
from terminaltexteffects.effects.effect_thunderstorm import Thunderstorm, ThunderstormConfig
from terminaltexteffects.effects.effect_wipe import Wipe
from terminaltexteffects.engine import _recording as recording_module
from terminaltexteffects.engine import terminal as terminal_module
from terminaltexteffects.engine._recording import MAGIC, RecordingHeader, RecordingReader, RecordingWriter
from terminaltexteffects.engine.base_effect import BaseEffectIterator
from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.utils import ansitools, export

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

pytestmark = [pytest.mark.smoke]

INPUT = "Hello\nWorld"


def _run(monkeypatch: pytest.MonkeyPatch, *arguments: str) -> None:
    monkeypatch.setattr(sys, "argv", ["tte", *arguments])
    __main__.main()


def _run_error(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], *arguments: str) -> str:
    with pytest.raises(SystemExit) as error:
        _run(monkeypatch, *arguments)
    assert error.value.code == 1
    return capsys.readouterr().err


def _write_recording(path: Path, frames: list[str], width: int = 1, height: int = 1, frame_rate: int = 30) -> Path:
    with RecordingWriter(path, RecordingHeader("test", width, height, frame_rate)) as writer:
        writer.begin_segment("test")
        for frame in frames:
            writer.write_frame(frame)
    return path


def _read_frames(path: Path) -> tuple[RecordingHeader, list[str], list[str]]:
    with RecordingReader(path, keep_segment_names=True) as reader:
        frames = list(reader.frames())
        return reader.header, frames, reader.segments


@pytest.fixture
def piped_input(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide fixed piped input."""
    monkeypatch.setattr(Terminal, "get_piped_input", lambda: INPUT)


@pytest.fixture
def terminal_size(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Report an 80x24 terminal to playback."""
    size = Mock(return_value=os.terminal_size((80, 24)))
    monkeypatch.setattr(__main__.shutil, "get_terminal_size", size)
    return size


@pytest.fixture
def printed(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Capture frames passed to `Terminal.print` without terminal cursor control."""
    output = Mock()
    monkeypatch.setattr(Terminal, "prep_canvas", Mock())
    monkeypatch.setattr(Terminal, "restore_cursor", Mock())
    monkeypatch.setattr(Terminal, "print", output)
    return output


def _printed_frames(output: Mock) -> list[str]:
    return [call.args[0] for call in output.call_args_list]


@pytest.mark.usefixtures("piped_input")
def test_record_matches_live_frames(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A recording holds exactly the frames the effect yields for the same seed and canvas."""
    path = tmp_path / "wipe.tterec"
    _run(monkeypatch, "--record", str(path), "--seed", "7", "wipe")
    random.seed(7)
    config = TerminalConfig._build_config()
    config.frame_rate = 0
    config.ignore_terminal_dimensions = True
    expected = list(Wipe(INPUT, terminal_config=config))
    header, frames, segments = _read_frames(path)
    assert frames == expected
    assert segments == ["wipe"]
    assert (header.width, header.height, header.frame_rate) == (5, 2, 60)
    assert f"Recorded {len(expected)} frames in 1 segment (5x2 at 60 fps)" in capsys.readouterr().err


@pytest.mark.usefixtures("piped_input")
def test_record_does_not_write_to_terminal_or_sleep(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Recording renders without terminal output or frame-rate sleeps."""
    sleep = Mock()
    monkeypatch.setattr(terminal_module.time, "sleep", sleep)
    _run(monkeypatch, "--record", str(tmp_path / "out.tterec"), "--frame-rate", "1", "wipe")
    sleep.assert_not_called()
    assert capsys.readouterr().out == ""


@pytest.mark.usefixtures("piped_input")
def test_record_random_effects_as_segments(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Random repeats record one segment per selected effect, all with the same geometry."""
    path = tmp_path / "playlist.tterec"
    _run(
        monkeypatch,
        "--record",
        str(path),
        "--random-effect",
        "--include-effects",
        "wipe",
        "print",
        "slide",
        "--repeat",
        "3",
        "--seed",
        "3",
    )
    header, frames, segments = _read_frames(path)
    assert len(segments) == 3
    assert set(segments) <= {"wipe", "print", "slide"}
    assert all(frame.count("\n") == header.height - 1 for frame in frames)


@pytest.mark.usefixtures("piped_input")
def test_record_repeat_records_fresh_playbacks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Repeating a fixed effect records each playback as its own segment."""
    path = tmp_path / "out.tterec"
    _run(monkeypatch, "--record", str(path), "--repeat", "2", "wipe")
    _, frames, segments = _read_frames(path)
    assert segments == ["wipe", "wipe"]
    assert frames[: len(frames) // 2] == frames[len(frames) // 2 :]


@pytest.mark.usefixtures("piped_input")
def test_record_interrupt_leaves_no_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Interrupting a recording exits with status 1 and leaves no partial file."""
    original_frame = BaseEffectIterator.frame
    frames = 0

    def interrupting_frame(self: BaseEffectIterator) -> str:
        nonlocal frames
        frames += 1
        if frames == 3:
            raise KeyboardInterrupt
        return original_frame.fget(self)  # type: ignore[misc]

    monkeypatch.setattr(BaseEffectIterator, "frame", property(interrupting_frame))
    with pytest.raises(SystemExit) as error:
        _run(monkeypatch, "--record", str(tmp_path / "out.tterec"), "wipe")
    assert error.value.code == 1
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (("--repeat", "0", "wipe"), "--record cannot be combined with --repeat 0."),
        (("--frame-rate", "0", "wipe"), "--record requires --frame-rate greater than 0."),
    ],
)
@pytest.mark.usefixtures("piped_input")
def test_record_rejects_invalid_options(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    arguments: tuple[str, ...],
    message: str,
) -> None:
    """Infinite repeats and unthrottled frame rates cannot be recorded."""
    assert message in _run_error(monkeypatch, capsys, "--record", str(tmp_path / "out.tterec"), *arguments)
    assert list(tmp_path.iterdir()) == []


def test_record_reports_unsupported_input(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """Input the engine rejects fails the recording with an error and leaves no file."""
    monkeypatch.setattr(Terminal, "get_piped_input", lambda: "Hello\x1b]0;title\x07")
    error = _run_error(monkeypatch, capsys, "--record", str(tmp_path / "out.tterec"), "wipe")
    assert "Unsupported ANSI/control sequence" in error
    assert list(tmp_path.iterdir()) == []


@pytest.mark.usefixtures("piped_input")
def test_record_reports_unwritable_path(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """A recording path in a missing directory fails with a clear error."""
    error = _run_error(monkeypatch, capsys, "--record", str(tmp_path / "missing" / "out.tterec"), "wipe")
    assert "Cannot write recording" in error


def test_play_rejects_record_combination(capsys: pytest.CaptureFixture[str]) -> None:
    """--record and --play are mutually exclusive at parse time."""
    parser, _ = __main__.build_parser(include_user_effects=False)
    with pytest.raises(SystemExit) as error:
        parser.parse_args(["--record", "a.tterec", "--play", "b.tterec"])
    assert error.value.code == 2
    assert "not allowed with argument" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (("--play", "x.tterec", "wipe"), "--play cannot be combined"),
        (("--play", "x.tterec", "--random-effect"), "--play cannot be combined"),
        (("--play", "x.tterec", "-i", "input.txt"), "--play cannot be combined"),
        (("--shuffle", "wipe"), "Error: --shuffle requires --play."),
        (
            ("--record", "out.tterec", "--hold", "1", "wipe"),
            "Error: --hold cannot be combined with --record, which displays nothing.",
        ),
        (
            ("--record", "out.tterec", "--alt-screen", "wipe"),
            "Error: --alt-screen cannot be combined with --record, which displays nothing.",
        ),
        (
            ("--record", "out.tterec", "--hold", "0", "wipe"),
            "Error: --hold cannot be combined with --record, which displays nothing.",
        ),
        (
            ("--record", "out.tterec", "--hold=0", "wipe"),
            "Error: --hold cannot be combined with --record, which displays nothing.",
        ),
        (
            ("--record", "out.tterec", "--alt-s", "wipe"),
            "Error: --alt-screen cannot be combined with --record, which displays nothing.",
        ),
        (
            ("--record", "out.tterec", "--hold", "1", "--alt-screen", "wipe"),
            "Error: --hold and --alt-screen cannot be combined with --record, which displays nothing.",
        ),
    ],
)
@pytest.mark.usefixtures("piped_input")
def test_playback_option_conflicts(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    arguments: tuple[str, ...],
    message: str,
) -> None:
    """Playback-only and display options are rejected where they do not apply."""
    assert message in _run_error(monkeypatch, capsys, *arguments)


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        (["--record", "x.tterec", "--hold", "0", "wipe"], {"record", "hold"}),
        (["--record", "x.tterec", "--frame-rate", "30", "matrix", "--rain-time", "2"], {"record", "frame_rate"}),
        (["--record", "x.tterec", "plugindemo", "--hold", "3"], {"record"}),
        (["--record", "x.tterec", "plugindemo", "--alt-screen"], {"record"}),
    ],
)
def test_options_given_ignores_options_after_the_effect(arguments: list[str], expected: set[str]) -> None:
    """Only global options before the effect name count; an effect's own same-named options do not."""
    assert set(__main__._options_given(arguments)) == expected


@pytest.fixture
def unreachable_recordings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail the test if playback looks for recordings."""

    def fail(_path: Path) -> list[Path]:
        msg = "rejected options must fail before any recording is read"
        raise AssertionError(msg)

    monkeypatch.setattr(__main__, "_find_recordings", fail)


@pytest.mark.parametrize(
    ("arguments", "option"),
    [
        (("--canvas-width", "80"), "--canvas-width"),
        (("--canvas-height", "24"), "--canvas-height"),
        (("--anchor-text", "c"), "--anchor-text"),
        (("--xterm-colors",), "--xterm-colors"),
        (("--no-color",), "--no-color"),
        (("--terminal-background-color", "000000"), "--terminal-background-color"),
        (("--existing-color-handling", "always"), "--existing-color-handling"),
        (("--tab-width", "8"), "--tab-width"),
        (("--wrap-text",), "--wrap-text"),
        (("--ignore-terminal-dimensions",), "--ignore-terminal-dimensions"),
        (("--include-effects", "wipe"), "--include-effects"),
        (("--exclude-effects", "wipe"), "--exclude-effects"),
        (("--anchor-t", "c"), "--anchor-text"),
        (("--canvas-width=-1",), "--canvas-width"),
        (("--existing-color-handling=ignore",), "--existing-color-handling"),
        (("--no-c",), "--no-color"),
    ],
)
@pytest.mark.usefixtures("unreachable_recordings")
def test_play_rejects_recording_time_options(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    arguments: tuple[str, ...],
    option: str,
) -> None:
    """Options fixed when a recording is made fail with --play, even abbreviated or given their default value."""
    with pytest.raises(SystemExit) as error:
        _run(monkeypatch, "--play", "x.tterec", *arguments)
    assert error.value.code == 1
    output = capsys.readouterr()
    assert output.err == (
        f"Error: {option} cannot be used with --play; canvas, text, color, and effect-selection options are "
        "fixed when a recording is made.\n"
    )
    assert output.out == ""


@pytest.mark.usefixtures("unreachable_recordings")
def test_play_rejection_names_every_option(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """All offending options are named together."""
    error = _run_error(
        monkeypatch,
        capsys,
        "--play",
        "x.tterec",
        "--no-color",
        "--anchor-text",
        "c",
        "--canvas-width",
        "10",
    )
    assert "Error: --canvas-width, --anchor-text, and --no-color cannot be used with --play" in error


@pytest.mark.usefixtures("terminal_size")
def test_play_accepts_playback_options(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, printed: Mock) -> None:
    """Options that playback honors remain accepted with --play."""
    path = _write_recording(tmp_path / "a.tterec", ["A"])
    _run(
        monkeypatch,
        "--play",
        str(path),
        "--frame-rate",
        "0",
        "--anchor-canvas",
        "c",
        "--reuse-canvas",
        "--no-eol",
        "--no-restore-cursor",
        "--seed",
        "1",
        "--repeat",
        "1",
        "--hold",
        "0",
        "--shuffle",
    )
    (frame,) = _printed_frames(printed)
    # A 1x1 canvas centered in 80x24: 39 columns from the left and 11 blank rows below.
    assert frame.split("\n") == [" " * 39 + "A", *[" " * 40] * 11]


@pytest.mark.usefixtures("piped_input", "terminal_size")
def test_play_round_trip_matches_recording(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, printed: Mock) -> None:
    """Playback prints every recorded frame, placed on the anchored canvas."""
    path = tmp_path / "wipe.tterec"
    _run(monkeypatch, "--record", str(path), "wipe")
    _, frames, _ = _read_frames(path)
    stdin = Mock(side_effect=AssertionError("playback must not read stdin"))
    monkeypatch.setattr(Terminal, "get_piped_input", stdin)
    _run(monkeypatch, "--play", str(path), "--frame-rate", "0")
    assert _printed_frames(printed) == frames


@pytest.mark.usefixtures("terminal_size")
def test_play_directory_in_filename_order(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, printed: Mock) -> None:
    """Directory playback uses top-level .tterec files in filename order and ignores others."""
    _write_recording(tmp_path / "b.tterec", ["B"])
    _write_recording(tmp_path / "a.tterec", ["A"])
    _write_recording(tmp_path / "c.tterec", ["C"])
    (tmp_path / "notes.txt").write_text("ignored")
    (tmp_path / "nested").mkdir()
    _write_recording(tmp_path / "nested" / "0.tterec", ["N"])
    _run(monkeypatch, "--play", str(tmp_path), "--frame-rate", "0", "--repeat", "2")
    assert _printed_frames(printed) == ["A", "B", "C", "A", "B", "C"]


@pytest.mark.usefixtures("terminal_size")
def test_play_shuffle_is_reproducible_with_seed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, printed: Mock) -> None:
    """Shuffled order changes with each pass and repeats for the same seed."""
    for name in "ABCDEFGH":
        _write_recording(tmp_path / f"{name}.tterec", [name])
    arguments = ("--play", str(tmp_path), "--frame-rate", "0", "--shuffle", "--seed", "5", "--repeat", "2")
    _run(monkeypatch, *arguments)
    first_run = _printed_frames(printed)
    printed.reset_mock()
    _run(monkeypatch, *arguments)
    assert _printed_frames(printed) == first_run
    assert sorted(first_run[:8]) == list("ABCDEFGH")
    assert first_run[:8] != list("ABCDEFGH")
    assert first_run[:8] != first_run[8:]


@pytest.mark.usefixtures("terminal_size", "printed")
def test_play_hold_after_every_recording(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """--hold pauses after every recording played, including the last."""
    _write_recording(tmp_path / "a.tterec", ["A"])
    _write_recording(tmp_path / "b.tterec", ["B"])
    sleep = Mock()
    monkeypatch.setattr(__main__.time, "sleep", sleep)
    _run(monkeypatch, "--play", str(tmp_path), "--frame-rate", "0", "--hold", "1.5", "--repeat", "2")
    assert [call.args[0] for call in sleep.call_args_list] == [1.5, 1.5, 1.5, 1.5]


@pytest.mark.usefixtures("terminal_size")
def test_play_stops_repeating_when_a_pass_has_no_frames(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    printed: Mock,
) -> None:
    """Endless repeats of recordings without frames end instead of spinning, as live replay does."""
    path = _write_recording(tmp_path / "empty.tterec", [])
    opened = Mock(wraps=__main__._open_validated_recording)
    monkeypatch.setattr(__main__, "_open_validated_recording", opened)
    _run(monkeypatch, "--play", str(path), "--repeat", "0")
    printed.assert_not_called()
    assert opened.call_count == 1


@pytest.mark.usefixtures("terminal_size", "printed")
def test_play_hold_skips_recordings_without_frames(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """--hold follows only recordings that showed a frame."""
    _write_recording(tmp_path / "a.tterec", [])
    _write_recording(tmp_path / "b.tterec", ["B"])
    _write_recording(tmp_path / "c.tterec", ["C"])
    sleep = Mock()
    monkeypatch.setattr(__main__.time, "sleep", sleep)
    _run(monkeypatch, "--play", str(tmp_path), "--frame-rate", "0", "--hold", "2")
    assert [call.args[0] for call in sleep.call_args_list] == [2.0, 2.0]


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", "-1", "86400.5", "1e300", "abc"])
def test_hold_rejects_values_outside_finite_range(capsys: pytest.CaptureFixture[str], value: str) -> None:
    """--hold accepts only finite durations from 0 to 86400 seconds, rejected at parse time."""
    parser, _ = __main__.build_parser(include_user_effects=False)
    with pytest.raises(SystemExit) as error:
        parser.parse_args(["--play", "x.tterec", "--hold", value])
    assert error.value.code == 2
    assert "--hold" in capsys.readouterr().err


@pytest.mark.parametrize(("value", "expected"), [("0", 0.0), ("2.5", 2.5), ("86400", 86400.0)])
def test_hold_accepts_finite_range(value: str, expected: float) -> None:
    """--hold accepts 0 through 86400 seconds."""
    parser, _ = __main__.build_parser(include_user_effects=False)
    assert parser.parse_args(["--play", "x.tterec", "--hold", value]).hold == expected


@pytest.mark.usefixtures("terminal_size", "printed")
def test_play_uses_recorded_frame_rate_unless_overridden(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Playback paces at the recorded rate by default and at --frame-rate when given."""
    path = _write_recording(tmp_path / "a.tterec", ["A", "B", "C"], frame_rate=25)
    rates: list[int] = []
    original_pacer = __main__._FramePacer

    def recording_pacer(frame_rate: int) -> __main__._FramePacer:
        rates.append(frame_rate)
        return original_pacer(0)

    monkeypatch.setattr(__main__, "_FramePacer", recording_pacer)
    _run(monkeypatch, "--play", str(path))
    _run(monkeypatch, "--play", str(path), "--frame-rate", "60")
    _run(monkeypatch, "--play", str(path), "--frame-rate", "0")
    assert rates == [25, 60, 0]


def test_frame_pacer_keeps_a_fixed_schedule(monkeypatch: pytest.MonkeyPatch) -> None:
    """Frames are due at fixed intervals, and a stall restarts the schedule instead of bursting."""
    now = [100.0]
    sleeps: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleeps.append(round(seconds, 6))
        now[0] += seconds

    monkeypatch.setattr(__main__.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(__main__.time, "sleep", fake_sleep)
    pacer = __main__._FramePacer(10)
    pacer.wait()  # first frame is immediate
    now[0] += 0.03  # rendering took 30 ms
    pacer.wait()
    pacer.wait()
    now[0] += 1.0  # stall
    pacer.wait()
    pacer.wait()
    assert sleeps == [0.07, 0.1, 0.1]


@pytest.mark.usefixtures("printed")
def test_play_refuses_terminal_smaller_than_canvas(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    terminal_size: Mock,
) -> None:
    """Playback exits with both sizes when the recording does not fit."""
    path = _write_recording(tmp_path / "wide.tterec", ["abcd\nabcd"], width=4, height=2)
    terminal_size.return_value = os.terminal_size((3, 24))
    error = _run_error(monkeypatch, capsys, "--play", str(path))
    assert "Recording canvas is 4x2 but the terminal is 3x24" in error
    terminal_size.return_value = os.terminal_size((80, 1))
    assert "terminal is 80x1" in _run_error(monkeypatch, capsys, "--play", str(path))


@pytest.mark.parametrize(
    ("anchor", "expected_full", "expected_small"),
    [
        ("sw", ["abcd", "abcd", "abcd"], ["    ", "    ", "xy  "]),
        ("c", [" abcd", " abcd", " abcd", "     "], ["     ", "  xy ", "     ", "     "]),
        ("ne", ["  abcd", "  abcd", "  abcd", *["      "] * 3], ["    xy", *["      "] * 5]),
    ],
)
def test_play_places_mixed_size_recordings_on_anchored_canvas(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    terminal_size: Mock,
    printed: Mock,
    anchor: str,
    expected_full: list[str],
    expected_small: list[str],
) -> None:
    """Smaller recordings are anchored inside the largest canvas, which is anchored in the terminal."""
    _write_recording(tmp_path / "a.tterec", ["abcd\nabcd\nabcd"], width=4, height=3)
    _write_recording(tmp_path / "b.tterec", ["xy"], width=2, height=1)
    terminal_size.return_value = os.terminal_size((6, 6))
    _run(monkeypatch, "--play", str(tmp_path), "--frame-rate", "0", "--anchor-canvas", anchor)
    full, small = _printed_frames(printed)
    assert full.split("\n") == expected_full
    assert small.split("\n") == expected_small


@pytest.mark.usefixtures("terminal_size")
def test_play_validates_every_recording_before_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    printed: Mock,
) -> None:
    """An invalid recording anywhere in a directory fails before any frame is shown."""
    _write_recording(tmp_path / "a.tterec", ["A"])
    (tmp_path / "b.tterec").write_bytes(b"not a recording")
    error = _run_error(monkeypatch, capsys, "--play", str(tmp_path))
    assert "b.tterec: File is not a TerminalTextEffects recording." in error
    printed.assert_not_called()


def _write_bad_frame_recording(path: Path) -> None:
    header = json.dumps({"tte_version": "test", "width": 1, "height": 1, "frame_rate": 30}).encode()
    segment = json.dumps({"effect": "test"}).encode()
    frame = b"\x1b[2J"
    records = b"".join(
        struct.pack("<cI", tag, len(data)) + data for tag, data in ((b"H", header), (b"S", segment), (b"F", frame))
    )
    path.write_bytes(MAGIC + b"\x01" + zlib.compress(records))


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        (lambda path: _write_recording(path, ["AB"], width=2), "a.tterec: Recording changed after validation."),
        (_write_bad_frame_recording, "a.tterec: Recording changed after validation."),
    ],
)
@pytest.mark.usefixtures("terminal_size")
def test_play_reports_recording_replaced_after_validation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    replacement: Callable[[Path], object],
    message: str,
) -> None:
    """A recording replaced between validation and playback fails with its path and restores the terminal."""
    path = _write_recording(tmp_path / "a.tterec", ["A"])
    original_validate = __main__._validate_recordings

    def validate_then_replace(paths: list[Path]) -> dict[Path, __main__._ValidatedRecording]:
        recordings = original_validate(paths)
        replacement(path)
        return recordings

    monkeypatch.setattr(__main__, "_validate_recordings", validate_then_replace)
    with pytest.raises(SystemExit) as exit_info:
        _run(monkeypatch, "--play", str(path), "--frame-rate", "0")
    assert exit_info.value.code == 1
    output = capsys.readouterr()
    assert message in output.err
    assert output.out.endswith(ansitools.reset_all() + ansitools.show_cursor() + "\n")


@pytest.mark.usefixtures("terminal_size")
def test_play_large_recording_validates_frames_during_playback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """Recordings too large to verify by digest have every frame validated again as they play."""
    monkeypatch.setattr(__main__, "_MAX_VERIFIED_RECORDING_BYTES", 0)
    path = _write_recording(tmp_path / "a.tterec", ["A"])
    original_validate = __main__._validate_recordings

    def validate_then_replace(paths: list[Path]) -> dict[Path, __main__._ValidatedRecording]:
        recordings = original_validate(paths)
        _write_bad_frame_recording(path)
        return recordings

    monkeypatch.setattr(__main__, "_validate_recordings", validate_then_replace)
    error = _run_error(monkeypatch, capsys, "--play", str(path), "--frame-rate", "0")
    assert "a.tterec: Frame contains an unsupported control or escape sequence" in error


@pytest.mark.usefixtures("terminal_size")
def test_play_verified_recording_skips_repeated_frame_checks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    printed: Mock,
) -> None:
    """Frames are validated once before playback, not again on each repeat of a verified recording."""
    path = _write_recording(tmp_path / "a.tterec", ["A", "B", "C"])
    checked: list[str] = []
    original_validate_frame = recording_module.validate_frame

    def counting_validate_frame(frame: str, width: int, height: int) -> None:
        checked.append(frame)
        original_validate_frame(frame, width, height)

    monkeypatch.setattr(recording_module, "validate_frame", counting_validate_frame)
    _run(monkeypatch, "--play", str(path), "--frame-rate", "0", "--repeat", "3")
    assert checked == ["A", "B", "C"]
    assert _printed_frames(printed) == ["A", "B", "C"] * 3


def test_play_reports_unreadable_directory(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """A directory that cannot be listed fails with a concise error instead of a traceback."""

    def denied_iterdir(_self: Path) -> Iterator[Path]:
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(type(tmp_path), "iterdir", denied_iterdir)
    error = _run_error(monkeypatch, capsys, "--play", str(tmp_path))
    assert f"Cannot read recording directory {str(tmp_path)!r}: Permission denied." in error


@pytest.mark.parametrize(
    ("make_path", "message"),
    [
        (lambda tmp: tmp / "missing.tterec", "Recording not found"),
        (lambda tmp: tmp, "No .tterec recordings found in directory"),
    ],
)
def test_play_reports_missing_recordings(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    make_path: object,
    message: str,
) -> None:
    """Missing files and empty directories fail with a clear error."""
    path = make_path(tmp_path)  # type: ignore[operator]
    assert message in _run_error(monkeypatch, capsys, "--play", str(path))


@pytest.mark.usefixtures("terminal_size")
def test_play_alt_screen_enters_and_restores(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """--alt-screen wraps playback in the alternate screen and restores the cursor first."""
    path = _write_recording(tmp_path / "a.tterec", ["A", "B"])
    _run(monkeypatch, "--play", str(path), "--frame-rate", "0", "--alt-screen")
    output = capsys.readouterr().out
    assert output.startswith(ansitools.enter_alternate_screen() + ansitools.hide_cursor())
    assert output.endswith(ansitools.show_cursor() + ansitools.reset_all() + ansitools.exit_alternate_screen())
    assert "A" in output
    assert "B" in output


@pytest.mark.parametrize("alt_screen", [False, True])
@pytest.mark.usefixtures("terminal_size")
def test_play_resets_text_attributes_left_by_recording(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    alt_screen: bool,  # noqa: FBT001
) -> None:
    """A final frame that leaves SGR attributes active is followed by a reset before control returns."""
    path = _write_recording(tmp_path / "a.tterec", ["\x1b[31mA"])
    arguments = ["--play", str(path), "--frame-rate", "0"]
    if alt_screen:
        arguments.append("--alt-screen")
    _run(monkeypatch, *arguments)
    output = capsys.readouterr().out
    assert output.rindex(ansitools.reset_all()) > output.rindex("\x1b[31mA")


@pytest.mark.parametrize("alt_screen", [False, True])
@pytest.mark.usefixtures("terminal_size")
def test_play_interrupt_restores_terminal(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    alt_screen: bool,  # noqa: FBT001
) -> None:
    """Ctrl+C during playback exits with status 1 after restoring the cursor and screen."""
    path = _write_recording(tmp_path / "a.tterec", ["A", "B", "C"])
    original_print = Terminal.print
    calls = 0

    def interrupting_print(self: Terminal, output: str) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise KeyboardInterrupt
        original_print(self, output)

    monkeypatch.setattr(Terminal, "print", interrupting_print)
    arguments = ["--play", str(path), "--frame-rate", "0", "--repeat", "0"]
    if alt_screen:
        arguments.append("--alt-screen")
    with pytest.raises(SystemExit) as error:
        _run(monkeypatch, *arguments)
    assert error.value.code == 1
    output = capsys.readouterr().out
    if alt_screen:
        expected_end = ansitools.show_cursor() + ansitools.reset_all() + ansitools.exit_alternate_screen()
    else:
        expected_end = ansitools.reset_all() + ansitools.show_cursor() + "\n"
    assert output.endswith(expected_end)


@pytest.fixture
def fast_wall_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Advance wall-clock time 100 seconds per read, so any wall-clock phase would end at once."""
    wall_time = [0.0]

    def fast_monotonic() -> float:
        wall_time[0] += 100.0
        return wall_time[0]

    monkeypatch.setattr(terminal_module.time, "monotonic", fast_monotonic)


def _frame_clock_effect(
    effect_class: type[Matrix | Thunderstorm],
    config_class: type[MatrixConfig | ThunderstormConfig],
    option: str,
) -> Matrix | Thunderstorm:
    random.seed(0)
    effect_config = config_class._build_config()
    setattr(effect_config, option, 1)
    terminal_config = TerminalConfig._build_config()
    terminal_config.frame_rate = 20
    effect = effect_class(INPUT, effect_config, terminal_config)  # type: ignore[arg-type]
    effect._frame_clock = True
    return effect


@pytest.mark.usefixtures("fast_wall_clock")
def test_matrix_rain_follows_frame_clock() -> None:
    """Rain lasts `rain_time` x frame rate frames however fast frames are rendered."""
    iterator = iter(_frame_clock_effect(Matrix, MatrixConfig, "rain_time"))
    rain_frames = 0
    for _ in iterator:
        if iterator.phase != "rain":  # type: ignore[attr-defined]
            break
        rain_frames += 1
    assert 20 <= rain_frames <= 22


@pytest.mark.usefixtures("fast_wall_clock")
def test_thunderstorm_storm_follows_frame_clock() -> None:
    """The storm lasts at least `storm_time` x frame rate frames and ends once no strike is in progress.

    A lightning strike in progress at the deadline finishes before the storm ends, so only the lower bound
    is fixed.
    """
    iterator = iter(_frame_clock_effect(Thunderstorm, ThunderstormConfig, "storm_time"))
    storm_frames = 0
    for _ in iterator:
        if iterator.phase == "storm":  # type: ignore[attr-defined]
            storm_frames += 1
        elif storm_frames:
            break
    assert storm_frames >= 20
    assert iterator.terminal.clock() - iterator.storm_start_time >= 1  # type: ignore[attr-defined]
    assert not iterator.strike_in_progress  # type: ignore[attr-defined]


@pytest.fixture
def export_tools(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Report agg and gif2webp on `PATH`, and record their commands instead of running them."""
    commands: list[list[str]] = []

    def run(command: list[str]) -> None:
        commands.append(command)
        Path(command[-1]).write_bytes(command[0].encode())

    monkeypatch.setattr(export.shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setattr(export, "_run", run)
    return commands


@pytest.mark.usefixtures("piped_input")
@pytest.mark.parametrize(
    ("suffix", "commands", "tools"),
    [(".gif", ["agg", "gifsicle"], ["agg"]), (".WEBP", ["agg", "gif2webp"], ["agg", "gif2webp"])],
)
def test_record_converts_gif_and_webp_by_suffix(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    export_tools: list[list[str]],
    suffix: str,
    commands: list[str],
    tools: list[str],
) -> None:
    """A .gif or .webp path renders a recording and converts it at the recording frame rate."""
    path = tmp_path / f"out{suffix}"
    _run(monkeypatch, "--record", str(path), "--frame-rate", "24", "--repeat", "2", "wipe")
    assert [command[0] for command in export_tools] == commands
    agg = export_tools[0]
    assert agg[agg.index("--fps-cap") + 1] == "25"
    assert path.read_bytes() == commands[-1].encode()
    assert list(tmp_path.iterdir()) == [path]
    error = capsys.readouterr().err
    name = export.format_for(path).name
    assert f"frames to {name} with {' and '.join(tools)}\n" in error
    assert "frames in 2 segments" in error
    assert f"at 24 fps) to {path}" in error
    assert "\r" not in error


@pytest.mark.usefixtures("piped_input")
def test_record_shows_frame_count_on_a_terminal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    export_tools: list[list[str]],
) -> None:
    """On a terminal, the frame count updates in place and is erased before the next line."""
    monkeypatch.setattr(__main__, "_is_terminal", lambda _stream: True)
    monkeypatch.setattr(__main__, "_PROGRESS_INTERVAL", 0.0)
    _run(monkeypatch, "--record", str(tmp_path / "out.gif"), "wipe")
    error = capsys.readouterr().err
    assert error.startswith("\rRendering frame 1\rRendering frame 2")
    assert "\r\x1b[KDrawing " in error
    assert export_tools


@pytest.mark.usefixtures("piped_input")
def test_record_reports_missing_tools_before_rendering(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A missing converter fails with its name and source before any frame renders."""
    monkeypatch.setattr(export.shutil, "which", lambda name: None if name == "gif2webp" else f"/bin/{name}")
    monkeypatch.setattr(__main__, "_create_effect", Mock(side_effect=AssertionError("rendered")))
    error = _run_error(monkeypatch, capsys, "--record", str(tmp_path / "out.webp"), "wipe")
    assert error == "Error: WebP needs gif2webp from libwebp on PATH.\n"
    assert list(tmp_path.iterdir()) == []


def test_record_empty_input_skips_the_tool_check(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Empty input stays a successful no-op even when the converter is missing."""
    monkeypatch.setattr(Terminal, "get_piped_input", lambda: " \n")
    monkeypatch.setattr(export.shutil, "which", lambda _name: None)
    _run(monkeypatch, "--record", str(tmp_path / "out.gif"), "wipe")
    assert capsys.readouterr().err == ""
    assert list(tmp_path.iterdir()) == []


@pytest.mark.usefixtures("piped_input")
def test_record_conversion_failure_leaves_no_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A converter that fails reports its error and leaves no output."""

    def run(command: list[str]) -> None:
        message = f"{command[0]} exited with 2: bad font"
        raise export.ExportError(message)

    monkeypatch.setattr(export.shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setattr(export, "_run", run)
    error = _run_error(monkeypatch, capsys, "--record", str(tmp_path / "out.gif"), "wipe")
    assert error.endswith("Error: agg exited with 2: bad font\n")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.usefixtures("piped_input")
def test_record_interrupted_conversion_leaves_no_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ctrl+C while converting exits with status 1 and leaves no partial output."""

    def run(command: list[str]) -> None:
        Path(command[-1]).write_bytes(b"partial")
        raise KeyboardInterrupt

    monkeypatch.setattr(export.shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setattr(export, "_run", run)
    with pytest.raises(SystemExit) as error:
        _run(monkeypatch, "--record", str(tmp_path / "out.gif"), "wipe")
    assert error.value.code == 1
    assert list(tmp_path.iterdir()) == []
