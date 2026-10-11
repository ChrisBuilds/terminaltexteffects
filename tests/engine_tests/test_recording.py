"""Tests for the effect recording file format, its validation, and the frame clock."""

from __future__ import annotations

import json
import os
import struct
import sys
import zlib
from typing import TYPE_CHECKING

import pytest

from terminaltexteffects.engine import _recording, terminal
from terminaltexteffects.engine._recording import (
    MAGIC,
    RecordingError,
    RecordingHeader,
    RecordingReader,
    RecordingWriter,
    validate_frame,
)
from terminaltexteffects.engine.terminal import Terminal, TerminalConfig

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = [pytest.mark.smoke]

HEADER = RecordingHeader(tte_version="test", width=3, height=2, frame_rate=30)


def _record(tag: bytes, payload: bytes | dict[str, object]) -> bytes:
    data = json.dumps(payload).encode() if isinstance(payload, dict) else payload
    return struct.pack("<cI", tag, len(data)) + data


def _header_record(**overrides: object) -> bytes:
    fields: dict[str, object] = {"tte_version": "test", "width": 3, "height": 2, "frame_rate": 30}
    fields.update(overrides)
    return _record(b"H", fields)


def _write_raw(path: Path, *records: bytes, preamble: bytes = MAGIC + b"\x01", trailing: bytes = b"") -> Path:
    path.write_bytes(preamble + zlib.compress(b"".join(records)) + trailing)
    return path


def _read_all(path: Path) -> list[str]:
    with RecordingReader(path) as reader:
        return list(reader.frames())


def test_round_trip_preserves_frames_and_segments(tmp_path: Path) -> None:
    """Frames and segment names read back exactly as written."""
    frames = ["abc\n\x1b[38;2;255;0;0mx\x1b[0myz", "界a\n   ", "   \n   "]
    path = tmp_path / "out.tterec"
    with RecordingWriter(path, HEADER) as writer:
        writer.begin_segment("first")
        writer.write_frame(frames[0])
        writer.write_frame(frames[1])
        writer.begin_segment("second")
        writer.write_frame(frames[2])
    with RecordingReader(path) as reader:
        assert reader.header == HEADER
        assert list(reader.frames()) == frames
        assert reader.segments == ["first", "second"]
    with RecordingReader(path) as reader:
        assert reader.validate() == 3


def test_writer_discards_partial_recording_on_error(tmp_path: Path) -> None:
    """A failed recording leaves an existing destination untouched and no temporary files."""
    path = tmp_path / "out.tterec"
    path.write_text("original")

    def interrupted_recording() -> None:
        with RecordingWriter(path, HEADER) as writer:
            writer.begin_segment("effect")
            writer.write_frame("abc\nabc")
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        interrupted_recording()
    assert path.read_text() == "original"
    assert sorted(tmp_path.iterdir()) == [path]


def test_writer_rejects_unplayable_frames(tmp_path: Path) -> None:
    """Frames that playback would reject cannot be recorded."""
    path = tmp_path / "out.tterec"

    def record_short_frame() -> None:
        with RecordingWriter(path, HEADER) as writer:
            writer.begin_segment("effect")
            writer.write_frame("abc")

    with pytest.raises(RecordingError, match="rows"):
        record_short_frame()
    assert not path.exists()


def test_writer_rejects_oversized_frame(tmp_path: Path) -> None:
    """Frames larger than the canvas size limit cannot be recorded."""
    header = RecordingHeader(tte_version="test", width=1, height=1, frame_rate=30)
    path = tmp_path / "out.tterec"

    def record_oversized_frame() -> None:
        with RecordingWriter(path, header) as writer:
            writer.begin_segment("effect")
            writer.write_frame("x" * (header.max_frame_bytes + 1))

    with pytest.raises(RecordingError, match="the limit for this canvas"):
        record_oversized_frame()
    assert not path.exists()


def test_writer_removes_temporary_file_when_header_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failure while writing the preamble or header leaves no temporary file behind."""
    original_write_record = RecordingWriter._write_record

    def failing_write_record(self: RecordingWriter, tag: bytes, data: bytes) -> None:
        original_write_record(self, tag, data)
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(RecordingWriter, "_write_record", failing_write_record)
    with pytest.raises(OSError, match="No space left on device"):
        RecordingWriter(tmp_path / "out.tterec", HEADER)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission bits")
def test_writer_honors_umask(tmp_path: Path) -> None:
    """Recordings get ordinary file permissions rather than private temporary-file permissions."""
    previous_umask = os.umask(0o022)
    try:
        path = tmp_path / "out.tterec"
        with RecordingWriter(path, HEADER) as writer:
            writer.begin_segment("effect")
    finally:
        os.umask(previous_umask)
    assert path.stat().st_mode & 0o777 == 0o644


@pytest.mark.parametrize(
    "frame",
    [
        "abc\n\x1b[0mabc\x1b[0m",
        "a\x1b[1;38;5;196mb\x1b[0mc\nabc",
        "😀a\n界 ",
    ],
)
def test_validate_frame_accepts_text_and_sgr(frame: str) -> None:
    """Printable text and SGR sequences filling the canvas width are safe to replay."""
    validate_frame(frame, 3, 2)


def test_validate_frame_measures_high_diversity_rows() -> None:
    """Rows with many distinct wide and narrow symbols are measured correctly in one pass."""
    wide = "".join(chr(0x4E00 + index) for index in range(2000))
    narrow = "".join(chr(0x0100 + index) for index in range(96))
    row = wide + narrow
    validate_frame(f"{row}\n{row}", 4096, 2)
    with pytest.raises(RecordingError, match="4096 cells wide; expected 4095"):
        validate_frame(row, 4095, 1)


@pytest.mark.parametrize(
    ("frame", "match"),
    [
        ("abcd\nabc", "4 cells wide; expected 3"),
        ("abc\nab", "2 cells wide; expected 3"),
        ("abc\n\x1b[31m\x1b[0m", "0 cells wide; expected 3"),
        ("abc\n界界", "4 cells wide; expected 3"),
        ("abc\nab\u0301", "cannot be displayed on its own"),
    ],
)
def test_validate_frame_rejects_rows_not_matching_canvas_width(frame: str, match: str) -> None:
    """Every row must render exactly the recorded canvas width, so playback cannot wrap or leave stale cells."""
    with pytest.raises(RecordingError, match=match):
        validate_frame(frame, 3, 2)


@pytest.mark.parametrize(
    "frame",
    [
        "\x1b]52;c;aGVsbG8=\x07\nabc",  # OSC 52 clipboard write
        "\x1b]0;title\x1b\\\nabc",  # OSC window title
        "\x1b[2J\nabc",  # erase display
        "\x1b[6n\nabc",  # cursor position query
        "\x1b7\nabc",  # DEC save cursor
        "\x9b31m\nabc",  # C1 CSI
        "a\x07\nabc",  # BEL
        "a\rb\nabc",  # carriage return
        "a\tb\nabc",  # tab
        "abc\x1b",  # trailing ESC
        "\x1b[31\nabc",  # unterminated SGR
    ],
)
def test_validate_frame_rejects_control_and_escape_sequences(frame: str) -> None:
    """Any control or escape sequence other than SGR is rejected."""
    with pytest.raises(RecordingError, match="unsupported control or escape sequence"):
        validate_frame(frame, 3, 2)


@pytest.mark.parametrize("frame", ["abc", "a\nb\nc"])
def test_validate_frame_rejects_wrong_row_count(frame: str) -> None:
    """Frames must have exactly the recorded number of rows."""
    with pytest.raises(RecordingError, match="expected 2"):
        validate_frame(frame, 3, 2)


@pytest.mark.parametrize(
    ("fields", "match"),
    [
        ({"width": 0}, "width"),
        ({"height": _recording.MAX_DIMENSION + 1}, "height"),
        ({"frame_rate": 0}, "frame rate"),
    ],
)
def test_header_rejects_out_of_range_values(fields: dict[str, int], match: str) -> None:
    """Header dimensions and frame rate are bounded."""
    values = {"tte_version": "test", "width": 3, "height": 2, "frame_rate": 30}
    values.update(fields)
    with pytest.raises(RecordingError, match=match):
        RecordingHeader(**values)  # type: ignore[arg-type]


def test_reader_rejects_missing_file(tmp_path: Path) -> None:
    """Unreadable files produce a recording error."""
    with pytest.raises(RecordingError, match="Cannot read recording"):
        RecordingReader(tmp_path / "missing.tterec")


@pytest.mark.parametrize(
    ("preamble", "match"),
    [
        (b"NOTREC\x01", "not a TerminalTextEffects recording"),
        (MAGIC + b"\x02", "Unsupported recording format version: 2"),
    ],
)
def test_reader_rejects_bad_preamble(tmp_path: Path, preamble: bytes, match: str) -> None:
    """The magic bytes and format version are checked first."""
    path = _write_raw(tmp_path / "bad.tterec", _header_record(), preamble=preamble)
    with pytest.raises(RecordingError, match=match):
        RecordingReader(path)


def test_reader_rejects_file_ending_after_magic(tmp_path: Path) -> None:
    """A file too short to hold the format version is rejected."""
    path = tmp_path / "short.tterec"
    path.write_bytes(MAGIC)
    with pytest.raises(RecordingError, match="Unsupported recording format version: None"):
        RecordingReader(path)


@pytest.mark.parametrize(
    ("records", "match"),
    [
        ((_record(b"S", {"effect": "x"}),), "header is missing"),
        ((_record(b"H", b"not json"),), "not valid JSON"),
        ((_record(b"H", b"[1]"),), "not a JSON object"),
        ((_header_record(width="3"),), "'width' is missing or invalid"),
        ((_header_record(frame_rate=True),), "'frame_rate' is missing or invalid"),
        ((_header_record(width=0),), "width must be between"),
        ((_record(b"H", b"x" * 5000),), "limit is 4096 bytes"),
    ],
)
def test_reader_rejects_bad_header(tmp_path: Path, records: tuple[bytes, ...], match: str) -> None:
    """The header record must be present, well formed, and in range."""
    path = _write_raw(tmp_path / "bad.tterec", *records)
    with pytest.raises(RecordingError, match=match):
        RecordingReader(path)


@pytest.mark.parametrize(
    ("records", "match"),
    [
        ((_record(b"F", b"abc\nabc"),), "before any segment"),
        ((_record(b"S", {"effect": "x"}), _record(b"F", b"\xff\xfe\nabc")), "not valid UTF-8"),
        ((_record(b"S", {"effect": "x"}), _record(b"F", b"\x1b[2J\nabc")), "unsupported control"),
        ((_record(b"S", {"effect": 1}),), "'effect' is missing or invalid"),
        ((_record(b"X", b""),), "unknown record type"),
        ((_record(b"S", {"effect": "x"}), _record(b"F", b"abc\nabc")), "truncated"),
        (
            (_record(b"S", {"effect": "x"}), _record(b"F", b"abc\nabc"), _record(b"E", {"frame_count": 2})),
            "declares 2 frames but contains 1",
        ),
    ],
)
def test_reader_rejects_bad_records(tmp_path: Path, records: tuple[bytes, ...], match: str) -> None:
    """Every record after the header is validated while frames stream."""
    path = _write_raw(tmp_path / "bad.tterec", _header_record(), *records)
    with pytest.raises(RecordingError, match=match):
        _read_all(path)


def test_reader_rejects_oversized_frame_before_inflating(tmp_path: Path) -> None:
    """A frame larger than the canvas allows is rejected from its declared size alone."""
    path = tmp_path / "bomb.tterec"
    header = _header_record()
    declared = struct.pack("<cI", b"F", 2**31)
    # Only the declared size is present; the payload is never inflated.
    _write_raw(path, header, _record(b"S", {"effect": "x"}), declared)
    with pytest.raises(RecordingError, match=r"limit is \d+ bytes"):
        _read_all(path)


def test_reader_bounds_inflation_to_requested_sizes(tmp_path: Path) -> None:
    """Highly compressible trailing data is never inflated beyond what a record needs."""
    path = tmp_path / "bomb.tterec"
    filler = b"\0" * (64 * 1024 * 1024)
    _write_raw(path, _header_record(), filler)
    with RecordingReader(path) as reader:
        assert reader._inflater._decompressor.unconsumed_tail  # filler remains compressed
        with pytest.raises(RecordingError, match="unknown record type"):
            _read_all(path)


@pytest.mark.parametrize("cut", [1, 10, 30])
def test_reader_rejects_truncated_file(tmp_path: Path, cut: int) -> None:
    """Cutting bytes from a valid recording is detected."""
    path = tmp_path / "out.tterec"
    with RecordingWriter(path, HEADER) as writer:
        writer.begin_segment("effect")
        writer.write_frame("abc\nabc")
    data = path.read_bytes()
    path.write_bytes(data[:-cut])
    with pytest.raises(RecordingError, match=r"truncated|corrupt"):
        _read_all(path)


def test_reader_rejects_trailing_data(tmp_path: Path) -> None:
    """Data after the end record is rejected."""
    path = tmp_path / "out.tterec"
    with RecordingWriter(path, HEADER) as writer:
        writer.begin_segment("effect")
    path.write_bytes(path.read_bytes() + b"extra")
    with pytest.raises(RecordingError, match="unexpected data after its end record"):
        _read_all(path)


def test_reader_rejects_records_after_end(tmp_path: Path) -> None:
    """Records following the end record are rejected."""
    path = _write_raw(
        tmp_path / "bad.tterec",
        _header_record(),
        _record(b"S", {"effect": "x"}),
        _record(b"E", {"frame_count": 0}),
        _record(b"S", {"effect": "y"}),
    )
    with pytest.raises(RecordingError, match="unexpected data after its end record"):
        _read_all(path)


def test_reader_rejects_corrupt_compressed_data(tmp_path: Path) -> None:
    """Corrupt zlib data is reported as a recording error."""
    path = tmp_path / "bad.tterec"
    path.write_bytes(MAGIC + b"\x01" + b"\x78\x9c" + b"\xff" * 32)
    with pytest.raises(RecordingError, match="corrupt"):
        RecordingReader(path)


def test_frame_clock_advances_one_period_per_frame_without_sleeping(monkeypatch: pytest.MonkeyPatch) -> None:
    """The frame clock is independent of wall time and never sleeps."""
    config = TerminalConfig._build_config()
    config.frame_rate = 20
    frame_terminal = Terminal("abc", config, frame_clock=True)

    def fail_sleep(_: float) -> None:
        msg = "frame clock must not sleep"
        raise AssertionError(msg)

    monkeypatch.setattr(terminal.time, "sleep", fail_sleep)
    assert frame_terminal.clock() == 0.0
    for _ in range(10):
        frame_terminal.enforce_framerate()
    assert frame_terminal.clock() == pytest.approx(0.5)


def test_live_clock_uses_monotonic_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without a frame clock, the clock reads monotonic wall time."""
    live_terminal = Terminal("abc")
    monkeypatch.setattr(terminal.time, "monotonic", lambda: 123.5)
    assert live_terminal.clock() == 123.5


def test_frame_clock_requires_frame_rate() -> None:
    """A frame clock cannot advance at frame rate 0."""
    config = TerminalConfig._build_config()
    config.frame_rate = 0
    with pytest.raises(ValueError, match="frame rate greater than 0"):
        Terminal("abc", config, frame_clock=True)
