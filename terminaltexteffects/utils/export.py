"""Convert recordings to GIF or animated WebP.

Frames are drawn from the recording with Pillow, which `pip install 'terminaltexteffects[export]'` installs on Python
3.10 and later. Pillow is imported only when exporting, so the rest of TTE does not need it. `tte --record`, the
TUI's Export, and `tools/render_demos.py` for the documentation demos all use this module.
"""

from __future__ import annotations

import importlib.util
import secrets
import shutil
import sys
import tempfile
import typing
from pathlib import Path

from terminaltexteffects.engine._recording import RECORDING_SUFFIX


class ExportFormat(typing.NamedTuple):
    """An output format for recordings: its name, file suffix, and whether it is drawn with Pillow."""

    name: str
    suffix: str
    needs_pillow: bool


FORMATS = (
    ExportFormat("tterec", RECORDING_SUFFIX, needs_pillow=False),
    ExportFormat("GIF", ".gif", needs_pillow=True),
    ExportFormat("WebP", ".webp", needs_pillow=True),
)
"""Recording formats, the native recording first."""

INSTALL_HINT = "pip install 'terminaltexteffects[export]'"
"""The command that installs what GIF and WebP export needs."""

PILLOW_PYTHON = sys.version_info >= (3, 10)
"""Whether this Python can install a Pillow release the `export` extra allows, which needs 3.10 or later."""

END_HOLD = 2.0
"""Seconds the last frame of a GIF or WebP is shown before the animation repeats."""


class ExportError(Exception):
    """Raised when converting a recording fails."""


def format_for(path: Path) -> ExportFormat:
    """Return the format for `path`'s suffix, or the native recording format for any other suffix."""
    suffix = path.suffix.lower()
    return next((fmt for fmt in FORMATS if fmt.suffix == suffix), FORMATS[0])


def pillow_available() -> bool:
    """Return whether Pillow can be imported."""
    return importlib.util.find_spec("PIL") is not None


def format_problem(fmt: ExportFormat) -> str | None:
    """Return why `fmt` can't be used here and how to fix it, or `None`."""
    if not fmt.needs_pillow or pillow_available():
        return None
    if not PILLOW_PYTHON:
        return f"{fmt.name} export needs Python 3.10 or later."
    return f"{fmt.name} export needs Pillow; install it with: {INSTALL_HINT}"


def export_recording(
    recording: Path,
    output: Path,
    fmt: ExportFormat,
    *,
    fps: int,
    font: str | None = None,
    fallback_fonts: typing.Sequence[str] = (),
    start_hold: float = 0.0,
    end_hold: float = END_HOLD,
    minimize_size: bool = False,
) -> frozenset[str]:
    """Convert `recording` to `output` in the GIF or WebP format `fmt`, at most `fps` frames per second.

    The first frame is held for `start_hold` extra seconds and the last for `end_hold` seconds before the animation
    repeats. `font` and `fallback_fonts` choose the fonts, as `Fonts` describes, and `minimize_size` makes WebP files
    a few percent smaller at about three times the encoding time.

    The file is converted in a temporary directory and replaces `output` only when conversion completes, so a
    failed or interrupted export leaves no partial file.

    Returns:
        frozenset[str]: Symbols no installed font has, which are drawn as missing-glyph boxes.

    Raises:
        ExportError: If Pillow is missing, no font can be loaded, or the recording has no frames.
        OSError: If `output` cannot be written.

    """
    problem = format_problem(fmt)
    if problem is not None:
        raise ExportError(problem)
    from terminaltexteffects.utils import _animation  # noqa: PLC0415 (Pillow is optional)

    with tempfile.TemporaryDirectory(prefix="tte-export-") as folder:
        work = Path(folder)
        converted = work / f"effect{fmt.suffix}"
        try:
            fonts = _animation.Fonts(font, fallback_fonts)
            frames = _animation.draw_frames(recording, work, fps=fps, fonts=fonts, start_hold=start_hold)
            if fmt.suffix == ".gif":
                _animation.write_gif(frames, converted, end_hold=end_hold)
            else:
                _animation.write_webp(frames, converted, end_hold=end_hold, minimize_size=minimize_size)
        except _animation.RenderError as error:
            raise ExportError(str(error)) from error
        _replace(output, converted)
    return frames.missing


def _replace(output: Path, converted: Path) -> None:
    """Copy `converted` next to `output`, then move it into place so `output` is never left partly written."""
    temporary = output.with_name(f".{output.name}.{secrets.token_hex(8)}.tmp")
    try:
        shutil.copyfile(converted, temporary)
        temporary.replace(output)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
