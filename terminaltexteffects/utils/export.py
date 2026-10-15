"""Convert recordings to GIF or animated WebP.

A recording is converted to an asciicast holding only the effect canvas, which `agg` renders to a GIF. WebP output
converts that GIF with `gif2webp`, which keeps every pixel and frame delay. `tte --record`, the TUI's Export, and
`tools/render_demos.py` for the documentation demos all use this pipeline.
"""

from __future__ import annotations

import json
import secrets
import shutil
import subprocess
import tempfile
import typing
from pathlib import Path

from terminaltexteffects.engine._recording import RECORDING_SUFFIX, RecordingReader


class ExportFormat(typing.NamedTuple):
    """An output format for recordings: its name, file suffix, and the commands it needs on `PATH`."""

    name: str
    suffix: str
    tools: tuple[str, ...]


FORMATS = (
    ExportFormat("tterec", RECORDING_SUFFIX, ()),
    ExportFormat("GIF", ".gif", ("agg",)),
    ExportFormat("WebP", ".webp", ("agg", "gif2webp")),
)
"""Recording formats, the native recording first."""

TOOL_SOURCES = {
    "agg": "agg from github.com/asciinema/agg",
    "gif2webp": "gif2webp from libwebp",
}
"""Where to get each command an export format needs."""

END_HOLD = 2.0
"""Seconds the last frame of a GIF or WebP is shown before the animation repeats."""


class ExportError(Exception):
    """Raised when converting a recording fails."""


def format_for(path: Path) -> ExportFormat:
    """Return the format for `path`'s suffix, or the native recording format for any other suffix."""
    suffix = path.suffix.lower()
    return next((fmt for fmt in FORMATS if fmt.suffix == suffix), FORMATS[0])


def missing_tools(fmt: ExportFormat) -> list[str]:
    """Return the commands `fmt` needs that are not on `PATH`."""
    return [tool for tool in fmt.tools if shutil.which(tool) is None]


def format_problem(fmt: ExportFormat) -> str | None:
    """Return why `fmt` can't be used here, naming the missing commands and where to get them, or `None`."""
    missing = missing_tools(fmt)
    if not missing:
        return None
    return f"{fmt.name} needs " + " and ".join(TOOL_SOURCES.get(tool, tool) for tool in missing) + " on PATH."


def recording_to_cast(recording: Path, cast: Path, start_hold: float = 0.0) -> bool:
    """Write the recording as an asciicast v2 file holding only the canvas.

    Every frame is drawn from the top-left corner with the cursor hidden, at the recording's frame period.
    The first frame is shown for an extra `start_hold` seconds.

    Returns:
        bool: Whether any frame contains non-ASCII text, which needs the `resvg` renderer in `agg`.

    """
    non_ascii = False
    with RecordingReader(recording) as reader, cast.open("w", encoding="utf-8") as out:
        header = reader.header
        period = 1 / header.frame_rate
        out.write(json.dumps({"version": 2, "width": header.width, "height": header.height}) + "\n")
        for index, frame in enumerate(reader.frames()):
            non_ascii = non_ascii or not frame.isascii()
            prefix = "\x1b[?25l\x1b[2J\x1b[H" if index == 0 else "\x1b[H"
            time = 0.0 if index == 0 else start_hold + index * period
            out.write(json.dumps([round(time, 6), "o", prefix + frame.replace("\n", "\r\n")]) + "\n")
    return non_ascii


def _run(command: list[str]) -> None:
    executable = shutil.which(command[0])
    if executable is None:
        message = f"{command[0]} is not installed or not on PATH."
        raise ExportError(message)
    result = subprocess.run(  # noqa: S603 (separated arguments, no shell)
        [executable, *command[1:]],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        message = f"{command[0]} exited with {result.returncode}: {(result.stderr or result.stdout).strip()}"
        raise ExportError(message)


def export_recording(recording: Path, output: Path, fmt: ExportFormat, *, fps: int) -> None:
    """Convert `recording` to `output` in the GIF or WebP format `fmt`, at most `fps` frames per second.

    The file is converted in a temporary directory and replaces `output` only when conversion completes, so a
    failed or interrupted export leaves no partial file.

    Raises:
        ExportError: If a needed command is missing or fails.
        OSError: If `output` cannot be written.

    """
    with tempfile.TemporaryDirectory(prefix="tte-export-") as folder:
        work = Path(folder)
        cast = work / "effect.cast"
        non_ascii = recording_to_cast(recording, cast)
        gif = work / "effect.gif"
        _run(
            [
                "agg",
                "--quiet",
                "--theme",
                "asciinema",
                "--font-size",
                "14",
                "--fps-cap",
                str(fps),
                "--last-frame-duration",
                str(END_HOLD),
                *(["--renderer", "resvg"] if non_ascii else []),
                str(cast),
                str(gif),
            ],
        )
        converted = gif
        if fmt.suffix == ".webp":
            converted = work / "effect.webp"
            _run(["gif2webp", "-quiet", "-min_size", str(gif), "-o", str(converted)])
        _replace(output, converted)


def _replace(output: Path, converted: Path) -> None:
    """Copy `converted` next to `output`, then move it into place so `output` is never left partly written."""
    temporary = output.with_name(f".{output.name}.{secrets.token_hex(8)}.tmp")
    try:
        shutil.copyfile(converted, temporary)
        temporary.replace(output)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
