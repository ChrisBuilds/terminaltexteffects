"""Recording file format for pre-rendered effect frames.

A recording stores the frames an effect produced so they can be played back without running the effect.
The file starts with the `MAGIC` bytes and a one-byte format version, followed by a single zlib stream.
The stream holds tagged records, each a one-byte tag, a little-endian unsigned 32-bit payload length, and the
payload:

- `H` (once, first): JSON header with `tte_version`, `width`, `height`, and `frame_rate`.
- `S`: JSON segment metadata with the `effect` name. Each effect playback in the recording starts a segment.
- `F`: UTF-8 frame text, `height` rows joined by newlines. Rows contain printable text and SGR sequences only,
  and each row is exactly `width` terminal cells wide.
- `E` (once, last): JSON trailer with the total `frame_count`, used to detect truncated files.

Recordings are untrusted input whose bytes are written to the terminal, so `RecordingReader` validates every
record, bounds every payload size before decompressing it, rejects any escape or control sequence other than
SGR, and rejects rows that do not exactly fill the canvas width.
"""

from __future__ import annotations

import io
import json
import re
import secrets
import struct
import zlib
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, BinaryIO, cast

from terminaltexteffects.utils.exceptions import InvalidSymbolError
from terminaltexteffects.utils.exceptions.base_terminaltexteffects_exception import TerminalTextEffectsError
from terminaltexteffects.utils.terminal_text import get_symbol_cell_width

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path
    from types import TracebackType

MAGIC = b"TTEREC"
FORMAT_VERSION = 1
RECORDING_SUFFIX = ".tterec"
MAX_DIMENSION = 4096
MAX_FRAME_BYTES = 64 * 1024 * 1024
_MAX_BYTES_PER_CELL = 256
_MAX_METADATA_BYTES = 4096
_READ_CHUNK_SIZE = 64 * 1024
_RECORD_PREFIX = struct.Struct("<cI")
_HEADER_TAG = b"H"
_SEGMENT_TAG = b"S"
_FRAME_TAG = b"F"
_END_TAG = b"E"
_SGR_SEQUENCE = re.compile(r"\x1b\[[0-9;]*m")
# After SGR sequences are removed, any remaining C0/C1 control character other than newline, including ESC, is unsafe.
_CONTROL_CHARACTER = re.compile(r"[\x00-\x09\x0b-\x1f\x7f-\x9f]")


class RecordingError(TerminalTextEffectsError):
    """Raised when a recording cannot be written, or a recording file is invalid."""

    def __init__(self, message: str) -> None:
        """Initialize a `RecordingError`.

        Args:
            message (str): Description of the problem.

        """
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class RecordingHeader:
    """Metadata shared by every frame in a recording.

    Attributes:
        tte_version (str): TerminalTextEffects version that produced the recording.
        width (int): Canvas width, in terminal cells, of every frame.
        height (int): Canvas height, in rows, of every frame.
        frame_rate (int): Intended playback rate in frames per second.

    """

    tte_version: str
    width: int
    height: int
    frame_rate: int

    def __post_init__(self) -> None:
        """Validate header values.

        Raises:
            RecordingError: If a dimension or the frame rate is out of range.

        """
        for name in ("width", "height"):
            value = getattr(self, name)
            if not 1 <= value <= MAX_DIMENSION:
                msg = f"Recording {name} must be between 1 and {MAX_DIMENSION}, got {value}."
                raise RecordingError(msg)
        if self.frame_rate < 1:
            msg = f"Recording frame rate must be greater than 0, got {self.frame_rate}."
            raise RecordingError(msg)

    @property
    def max_frame_bytes(self) -> int:
        """Return the largest encoded frame accepted for this header's dimensions."""
        return min(self.width * self.height * _MAX_BYTES_PER_CELL + self.height, MAX_FRAME_BYTES)


def _text_cell_width(text: str) -> int:
    """Return the terminal-cell width of row text that contains no escape sequences.

    Raises:
        RecordingError: If the text contains a code point that cannot occupy its own terminal cells.

    """
    width = len(text)
    if text.isascii():
        return width
    # Count symbols in one linear pass, then measure each distinct non-ASCII symbol once.
    try:
        for symbol, count in Counter(text).items():
            if not symbol.isascii():
                width += (get_symbol_cell_width(symbol) - 1) * count
    except InvalidSymbolError as error:
        msg = f"Frame row contains a symbol that cannot be displayed on its own: {error.symbol!r}."
        raise RecordingError(msg) from error
    return width


def validate_frame(frame: str, width: int, height: int) -> None:
    """Check that frame text is safe to write to a terminal and fills exactly the recorded canvas.

    Args:
        frame (str): Frame text with rows joined by newlines.
        width (int): Expected width of every row, in terminal cells.
        height (int): Expected number of rows.

    Raises:
        RecordingError: If the frame contains a control or escape sequence other than SGR, has the wrong number of
            rows, or has a row that is not exactly `width` cells wide.

    """
    # A valid SGR sequence contains exactly one ESC, at its start, so removing them removes only the ESCs that
    # begin valid SGR sequences. Every other ESC and control character remains to be rejected.
    text = _SGR_SEQUENCE.sub("", frame)
    unsafe = _CONTROL_CHARACTER.search(text)
    if unsafe is not None:
        msg = f"Frame contains an unsupported control or escape sequence: {text[unsafe.start() : unsafe.end() + 8]!r}."
        raise RecordingError(msg)
    rows = text.split("\n")
    if len(rows) != height:
        msg = f"Frame has {len(rows)} rows; expected {height}."
        raise RecordingError(msg)
    for row in rows:
        row_width = _text_cell_width(row)
        if row_width != width:
            msg = f"Frame row is {row_width} cells wide; expected {width}."
            raise RecordingError(msg)


class RecordingWriter:
    """Write frames to a recording file.

    Frames are written to a temporary file next to `path`, which replaces `path` only when `close()` completes.
    Leaving the context manager with an exception discards the temporary file and leaves `path` unchanged.
    """

    def __init__(self, path: Path, header: RecordingHeader) -> None:
        """Open a temporary file and write the recording header.

        Args:
            path (Path): Destination recording path.
            header (RecordingHeader): Header describing every frame that will be written.

        """
        self.path = path
        self.header = header
        self.frame_count = 0
        # Exclusive creation with a random name honors the umask, unlike `tempfile.mkstemp()`.
        self._temporary_path = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
        self._file: BinaryIO = self._temporary_path.open("xb")
        self._compressor = zlib.compressobj(6)
        self._closed = False
        try:
            self._file.write(MAGIC + bytes((FORMAT_VERSION,)))
            self._write_json(
                _HEADER_TAG,
                {
                    "tte_version": header.tte_version,
                    "width": header.width,
                    "height": header.height,
                    "frame_rate": header.frame_rate,
                },
            )
        except BaseException:
            self.abort()
            raise

    def __enter__(self) -> RecordingWriter:
        """Return this writer."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Finish the recording, or discard it if the block raised."""
        if exc_type is None:
            self.close()
        else:
            self.abort()

    def begin_segment(self, effect_name: str) -> None:
        """Start a segment for the next effect playback.

        Args:
            effect_name (str): Name of the effect producing the following frames.

        """
        self._write_json(_SEGMENT_TAG, {"effect": effect_name})

    def write_frame(self, frame: str) -> None:
        """Validate and append one frame.

        Args:
            frame (str): Frame text with `header.height` rows joined by newlines.

        Raises:
            RecordingError: If the frame cannot be played back safely or exceeds the frame size limit.

        """
        data = frame.encode("utf-8")
        if len(data) > self.header.max_frame_bytes:
            msg = f"Frame is {len(data)} bytes; the limit for this canvas is {self.header.max_frame_bytes} bytes."
            raise RecordingError(msg)
        validate_frame(frame, self.header.width, self.header.height)
        self._write_record(_FRAME_TAG, data)
        self.frame_count += 1

    def close(self) -> None:
        """Write the trailer and move the finished recording into place."""
        if self._closed:
            return
        try:
            self._write_json(_END_TAG, {"frame_count": self.frame_count})
            self._file.write(self._compressor.flush())
            self._file.close()
            self._temporary_path.replace(self.path)
        except BaseException:
            self.abort()
            raise
        self._closed = True

    def abort(self) -> None:
        """Discard the partially written recording."""
        if self._closed:
            return
        self._closed = True
        self._file.close()
        self._temporary_path.unlink(missing_ok=True)

    def _write_json(self, tag: bytes, payload: dict[str, object]) -> None:
        self._write_record(tag, json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    def _write_record(self, tag: bytes, data: bytes) -> None:
        self._file.write(self._compressor.compress(_RECORD_PREFIX.pack(tag, len(data)) + data))


class _BoundedInflater:
    """Decompress a zlib stream on demand, never inflating more than the caller requests."""

    def __init__(self, file: BinaryIO) -> None:
        self._file = file
        self._decompressor = zlib.decompressobj()
        self._pending = b""

    def read_exact(self, size: int) -> bytes | None:
        """Return exactly `size` decompressed bytes, or `None` if the stream ends first.

        Raises:
            RecordingError: If the compressed data is corrupt.

        """
        parts: list[bytes] = []
        remaining = size
        try:
            while remaining:
                if not self._pending:
                    if self._decompressor.eof:
                        return None
                    self._pending = self._file.read(_READ_CHUNK_SIZE)
                    if not self._pending:
                        return None
                data = self._decompressor.decompress(self._pending, remaining)
                self._pending = self._decompressor.unconsumed_tail
                if self._decompressor.eof:
                    self._pending = b""
                parts.append(data)
                remaining -= len(data)
        except zlib.error as error:
            msg = f"Recording data is corrupt: {error}."
            raise RecordingError(msg) from error
        return b"".join(parts)

    def finish(self) -> None:
        """Check that the zlib stream ends here, complete and with no trailing data.

        Raises:
            RecordingError: If more records follow, the stream is incomplete, or data follows the stream.

        """
        if self.read_exact(1) is not None:
            msg = "Recording has unexpected data after its end record."
            raise RecordingError(msg)
        if not self._decompressor.eof:
            msg = "Recording is truncated."
            raise RecordingError(msg)
        if self._decompressor.unused_data or self._file.read(1):
            msg = "Recording has unexpected data after its end record."
            raise RecordingError(msg)


class RecordingReader:
    """Read and validate a recording file.

    The header is read and validated on construction. `frames()` streams the frames, validating each record as it
    is read, so a recording of any length plays back in constant memory. A reader can also read recording bytes
    already held in memory, such as bytes whose digest matches a previously validated recording.

    Attributes:
        path (Path): Recording file being read.
        header (RecordingHeader): Validated recording header.
        segment_count (int): Number of segments read so far by `frames()`.
        segments (list[str]): Effect names of the segments read so far by `frames()`, collected only when the
            reader was created with `keep_segment_names=True`. Untrusted recordings may contain any number of
            segments, so names are not retained by default.

    """

    def __init__(self, path: Path, data: bytes | None = None, *, keep_segment_names: bool = False) -> None:
        """Open a recording and read its header.

        Args:
            path (Path): Recording file to read, or the file `data` was read from.
            data (bytes | None, optional): Recording bytes to read instead of opening `path`. Defaults to None.
            keep_segment_names (bool, optional): Collect segment effect names in `segments`. Defaults to False.

        Raises:
            RecordingError: If the file cannot be read or does not start with a valid recording header.

        """
        self.path = path
        self.segment_count = 0
        self.segments: list[str] = []
        self._keep_segment_names = keep_segment_names
        if data is not None:
            self._file: BinaryIO = io.BytesIO(data)
        else:
            try:
                self._file = path.open("rb")
            except OSError as error:
                msg = f"Cannot read recording {str(path)!r}: {error.strerror or error}."
                raise RecordingError(msg) from error
        try:
            self.header = self._read_header()
        except BaseException:
            self._file.close()
            raise

    def __enter__(self) -> RecordingReader:
        """Return this reader."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the recording file."""
        self.close()

    def close(self) -> None:
        """Close the recording file."""
        self._file.close()

    def frames(self, *, validate_frames: bool = True) -> Iterator[str]:
        """Yield each frame in order.

        Args:
            validate_frames (bool, optional): Check each frame's content with `validate_frame()`. Pass `False` only
                for bytes already known to match a recording that was validated completely, such as by digest.
                Record structure and size limits are always checked. Defaults to True.

        Raises:
            RecordingError: If a record is malformed, a frame is unsafe or oversized, or the recording is truncated.

        """
        frame_count = 0
        while True:
            tag, data = self._read_record(self.header.max_frame_bytes)
            if tag == _SEGMENT_TAG:
                effect_name = cast("str", self._parse_json(data, {"effect": str})["effect"])
                self.segment_count += 1
                if self._keep_segment_names:
                    self.segments.append(effect_name)
            elif tag == _FRAME_TAG:
                if not self.segment_count:
                    msg = "Recording frame appears before any segment."
                    raise RecordingError(msg)
                try:
                    frame = data.decode("utf-8")
                except UnicodeDecodeError as error:
                    msg = "Recording frame is not valid UTF-8."
                    raise RecordingError(msg) from error
                if validate_frames:
                    validate_frame(frame, self.header.width, self.header.height)
                frame_count += 1
                yield frame
            elif tag == _END_TAG:
                trailer = self._parse_json(data, {"frame_count": int})
                if trailer["frame_count"] != frame_count:
                    msg = f"Recording declares {trailer['frame_count']} frames but contains {frame_count}."
                    raise RecordingError(msg)
                self._inflater.finish()
                return
            else:
                msg = f"Recording contains an unknown record type: {tag!r}."
                raise RecordingError(msg)

    def validate(self) -> int:
        """Read the whole recording, validating every record.

        Returns:
            int: Number of frames in the recording.

        """
        return sum(1 for _ in self.frames())

    def _read_header(self) -> RecordingHeader:
        preamble = self._file.read(len(MAGIC) + 1)
        if preamble[: len(MAGIC)] != MAGIC:
            msg = "File is not a TerminalTextEffects recording."
            raise RecordingError(msg)
        if preamble[len(MAGIC) :] != bytes((FORMAT_VERSION,)):
            version = preamble[len(MAGIC)] if len(preamble) > len(MAGIC) else None
            msg = f"Unsupported recording format version: {version}."
            raise RecordingError(msg)
        self._inflater = _BoundedInflater(self._file)
        tag, header_data = self._read_record()
        if tag != _HEADER_TAG:
            msg = "Recording header is missing."
            raise RecordingError(msg)
        fields = self._parse_json(header_data, {"tte_version": str, "width": int, "height": int, "frame_rate": int})
        return RecordingHeader(
            tte_version=cast("str", fields["tte_version"]),
            width=cast("int", fields["width"]),
            height=cast("int", fields["height"]),
            frame_rate=cast("int", fields["frame_rate"]),
        )

    def _read_record(self, max_frame_size: int = 0) -> tuple[bytes, bytes]:
        """Read one record, rejecting a payload larger than its tag allows before inflating it."""
        prefix = self._inflater.read_exact(_RECORD_PREFIX.size)
        if prefix is None:
            msg = "Recording is truncated."
            raise RecordingError(msg)
        tag, size = _RECORD_PREFIX.unpack(prefix)
        max_size = max_frame_size if tag == _FRAME_TAG else _MAX_METADATA_BYTES
        if size > max_size:
            msg = f"Recording record is {size} bytes; the limit is {max_size} bytes."
            raise RecordingError(msg)
        data = self._inflater.read_exact(size)
        if data is None:
            msg = "Recording is truncated."
            raise RecordingError(msg)
        return tag, data

    @staticmethod
    def _parse_json(data: bytes, schema: dict[str, type]) -> dict[str, object]:
        try:
            payload = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as error:
            msg = "Recording metadata is not valid JSON."
            raise RecordingError(msg) from error
        if not isinstance(payload, dict):
            msg = "Recording metadata is not a JSON object."
            raise RecordingError(msg)
        fields: dict[str, object] = {}
        for name, expected_type in schema.items():
            value = payload.get(name)
            # bool is an int subclass; reject it for integer fields.
            if not isinstance(value, expected_type) or isinstance(value, bool):
                msg = f"Recording metadata field {name!r} is missing or invalid."
                raise RecordingError(msg)
            fields[name] = value
        return fields
