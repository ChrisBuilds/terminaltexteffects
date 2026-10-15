"""Render a recording straight to an animated WebP, without an asciicast or GIF in between.

Each frame is drawn cell by cell with Pillow, in the same font, size, and colors `agg` uses for the GIF and WebP
exports, so the demos look the same while keeping every color and every frame. Only cells that changed since the
previous frame are redrawn, and frames identical to the one before are merged into a longer frame. `img2webp` from
libwebp encodes the frames, losslessly by default, or with near-lossless preprocessing when a level is given.

Block elements are drawn as filled rectangles and shades as blended colors, so they tile without gaps as they do
in most terminals. Symbols the main font lacks, such as the half-width katakana in `matrix`, are drawn with the
first fallback font that has them.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import typing
from dataclasses import dataclass
from functools import cache, lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from terminaltexteffects.engine._recording import RecordingReader
from terminaltexteffects.utils.hexterm import xterm_to_hex
from terminaltexteffects.utils.terminal_text import get_symbol_cell_width

if typing.TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

RGB = tuple[int, int, int]

BACKGROUND: RGB = (0x12, 0x13, 0x14)
"""The `asciinema` theme background `agg` uses."""

FOREGROUND: RGB = (0xCC, 0xCC, 0xCC)
"""The `asciinema` theme foreground `agg` uses."""

FONT_SIZE = 14
LINE_HEIGHT = 1.4
"""Font size in pixels and line height in font sizes, as `agg` draws them by default."""

FONT = "DejaVuSansMono.ttf"
"""The default font, found by name in the system font folders, with bold and oblique faces beside it."""

FALLBACK_FONTS = (
    "ipag.ttf",
    "NotoSansCJK-Regular.ttc",
    "NotoSansMonoCJKjp-Regular.otf",
    "msgothic.ttc",
    "YuGothR.ttc",
    "ヒラギノ角ゴシック W3.ttc",
    "Hiragino Sans GB.ttc",
    "wqy-zenhei.ttc",
    "unifont.otf",
)
"""Fonts tried, after any `fontconfig` match, for symbols the main font lacks."""

BOLD, DIM, ITALIC, UNDERLINE, REVERSE, HIDDEN, STRIKE = (1 << bit for bit in range(7))
_SGR_ATTRIBUTES = {1: BOLD, 2: DIM, 3: ITALIC, 4: UNDERLINE, 7: REVERSE, 8: HIDDEN, 9: STRIKE}
_SGR_RESETS = {22: BOLD | DIM, 23: ITALIC, 24: UNDERLINE, 27: REVERSE, 28: HIDDEN, 29: STRIKE}

BLOCKS = {
    "█": (0, 0, 1, 1),
    "▀": (0, 0, 1, 1 / 2),
    "▄": (0, 1 / 2, 1, 1),
    "▌": (0, 0, 1 / 2, 1),
    "▐": (1 / 2, 0, 1, 1),
    "▁": (0, 7 / 8, 1, 1),
    "▂": (0, 6 / 8, 1, 1),
    "▃": (0, 5 / 8, 1, 1),
    "▅": (0, 3 / 8, 1, 1),
    "▆": (0, 2 / 8, 1, 1),
    "▇": (0, 1 / 8, 1, 1),
    "▉": (0, 0, 7 / 8, 1),
    "▊": (0, 0, 6 / 8, 1),
    "▋": (0, 0, 5 / 8, 1),
    "▍": (0, 0, 3 / 8, 1),
    "▎": (0, 0, 2 / 8, 1),
    "▏": (0, 0, 1 / 8, 1),
    "▔": (0, 0, 1, 1 / 8),
    "▕": (7 / 8, 0, 1, 1),
}
"""Block elements, as the part of the cell each one fills: left, top, right, and bottom."""

SHADES = {"░": 1 / 4, "▒": 1 / 2, "▓": 3 / 4}
"""Shade characters, as the share of the foreground color blended into the background."""

_TOKEN = re.compile(r"\x1b\[([0-9;]*)m|(.)", re.DOTALL)


class Cell(typing.NamedTuple):
    """One terminal cell: its symbol, colors, and SGR attributes.

    The cell after a wide symbol holds an empty symbol, since the wide symbol covers it.
    """

    symbol: str
    fg: RGB
    bg: RGB
    attributes: int = 0


class RenderError(Exception):
    """Raised when a recording cannot be rendered to WebP."""


def _xterm(index: int) -> RGB:
    value = int(xterm_to_hex(index), 16)
    return (value >> 16, (value >> 8) & 0xFF, value & 0xFF)


@cache
def _apply_sgr(parameters: str, fg: RGB, bg: RGB, attributes: int) -> tuple[RGB, RGB, int]:
    """Return the colors and attributes after the SGR sequence with `parameters`."""
    values = [int(value) for value in parameters.split(";") if value] or [0]
    index = 0
    while index < len(values):
        value = values[index]
        if value == 0:
            fg, bg, attributes = FOREGROUND, BACKGROUND, 0
        elif value in _SGR_ATTRIBUTES:
            attributes |= _SGR_ATTRIBUTES[value]
        elif value in _SGR_RESETS:
            attributes &= ~_SGR_RESETS[value]
        elif value in (38, 48) and values[index + 1 : index + 2] == [2]:
            color = typing.cast("RGB", tuple(values[index + 2 : index + 5]))
            fg, bg = (color, bg) if value == 38 else (fg, color)
            index += 4
        elif value in (38, 48) and values[index + 1 : index + 2] == [5]:
            color = _xterm(values[index + 2])
            fg, bg = (color, bg) if value == 38 else (fg, color)
            index += 2
        elif value == 39:
            fg = FOREGROUND
        elif value == 49:
            bg = BACKGROUND
        elif 30 <= value <= 37 or 90 <= value <= 97:
            fg = _xterm(value - 30 if value < 90 else value - 82)
        elif 40 <= value <= 47 or 100 <= value <= 107:
            bg = _xterm(value - 40 if value < 100 else value - 92)
        index += 1
    return fg, bg, attributes


def parse_frame(frame: str, width: int, height: int) -> list[tuple[Cell, ...]]:
    """Return the frame as `height` rows of `width` cells.

    Colors and attributes carry over from one row to the next, as they do in a terminal.
    """
    state = (FOREGROUND, BACKGROUND, 0)
    rows: list[tuple[Cell, ...]] = []
    for line in frame.split("\n")[:height]:
        row, state = _parse_row(line, width, state)
        rows.append(row)
    rows += [(Cell(" ", FOREGROUND, BACKGROUND),) * width] * (height - len(rows))
    return rows


_State = tuple[RGB, RGB, int]


@lru_cache(maxsize=4096)
def _parse_row(line: str, width: int, state: _State) -> tuple[tuple[Cell, ...], _State]:
    """Return the cells of one row and the colors and attributes after it.

    Most rows repeat from one frame to the next, so parsed rows are cached, which also lets `FrameDrawer` skip them.
    """
    fg, bg, attributes = state
    row: list[Cell] = []
    for parameters, symbol in _TOKEN.findall(line):
        if not symbol:
            fg, bg, attributes = _apply_sgr(parameters, fg, bg, attributes)
            continue
        row.append(Cell(symbol, fg, bg, attributes))
        if get_symbol_cell_width(symbol) == 2:
            row.append(Cell("", fg, bg, attributes))
    row += [Cell(" ", FOREGROUND, BACKGROUND)] * (width - len(row))
    return tuple(row[:width]), (fg, bg, attributes)


@dataclass(frozen=True)
class Encoding:
    """How `img2webp` encodes the frames: losslessly, or with near-lossless preprocessing at `near_lossless`.

    Near-lossless levels run from 100 (off) down to 0, the strongest. Levels around 60 change pixel values by a few
    steps at most, which is invisible in terminal text and shrinks most demos by 10-25%.
    """

    near_lossless: int | None = None

    def file_options(self) -> list[str]:
        """Return the `img2webp` options that apply to the whole file."""
        options = ["-min_size", "-loop", "0"]
        if self.near_lossless is not None:
            options += ["-near_lossless", str(self.near_lossless)]
        return options


LOSSLESS = Encoding()


class Fonts:
    """The main font in each face, and fallback fonts for symbols it lacks."""

    def __init__(self, font: str, fallbacks: Sequence[str] = (), size: int = FONT_SIZE) -> None:
        """Load `font`, a path or a font file name in the system font folders, and its bold and oblique faces.

        Faces beside `font` named with `-Bold`, `-Oblique`, and `-BoldOblique` are used when they exist; otherwise
        every face is drawn with `font`. `fallbacks` are tried before `FALLBACK_FONTS` for missing symbols.

        Raises:
            RenderError: If `font` cannot be found or loaded.

        """
        self.size = size
        try:
            self.regular = ImageFont.truetype(font, size)
        except OSError as error:
            message = f"Cannot load the font {font!r} ({error}); install DejaVu Sans Mono or pass --font PATH."
            raise RenderError(message) from error
        path = Path(str(self.regular.path))
        faces = {}
        for attributes, suffix in ((BOLD, "Bold"), (ITALIC, "Oblique"), (BOLD | ITALIC, "BoldOblique")):
            face = path.with_name(f"{path.stem}-{suffix}{path.suffix}")
            faces[attributes] = ImageFont.truetype(str(face), size) if face.is_file() else self.regular
        self.faces = faces
        self.fallback_names = [*fallbacks, *FALLBACK_FONTS]
        self.cell_width = round(self.regular.getlength("M"))
        self.cell_height = round(size * LINE_HEIGHT)
        ascent, descent = self.regular.getmetrics()
        self.baseline = (self.cell_height - (ascent + descent)) // 2 + ascent
        self.warned: set[str] = set()

    def face(self, attributes: int) -> ImageFont.FreeTypeFont:
        """Return the main font face for the bold and italic `attributes`."""
        return self.faces.get(attributes & (BOLD | ITALIC), self.regular)

    def for_symbol(self, symbol: str, face: ImageFont.FreeTypeFont) -> ImageFont.FreeTypeFont:
        """Return `face` when it has `symbol`, otherwise the first fallback font that has it."""
        if _has_glyph(face, symbol):
            return face
        fallback = self._fallback(symbol)
        if fallback is None:
            if symbol not in self.warned:
                self.warned.add(symbol)
                print(f"No font has {symbol!r} (U+{ord(symbol):04X}); pass --fallback-font PATH.", file=sys.stderr)
            return face
        return fallback

    def _fallback(self, symbol: str) -> ImageFont.FreeTypeFont | None:
        for name in [*_fontconfig_match(symbol), *self.fallback_names]:
            font = _load_font(name, self.size)
            if font is not None and _has_glyph(font, symbol):
                return font
        return None


@cache
def _load_font(name: str, size: int) -> ImageFont.FreeTypeFont | None:
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return None


@cache
def _fontconfig_match(symbol: str) -> tuple[str, ...]:
    """Return the font `fontconfig` picks for `symbol`, preferring monospace fonts, when `fc-match` is installed."""
    executable = shutil.which("fc-match")
    if executable is None:
        return ()
    result = subprocess.run(  # noqa: S603 - Separated arguments; no shell.
        [executable, "-f", "%{file}", f"monospace:charset={ord(symbol):x}"],
        check=False,
        capture_output=True,
        text=True,
    )
    return (result.stdout,) if result.returncode == 0 and result.stdout else ()


@cache
def _has_glyph(font: ImageFont.FreeTypeFont, symbol: str) -> bool:
    """Return whether `font` draws `symbol` with its own glyph rather than its missing-glyph box."""
    return _glyph_pixels(font, symbol) != _glyph_pixels(font, "\U0010fffd")


def _glyph_pixels(font: ImageFont.FreeTypeFont, symbol: str) -> tuple[tuple[int, int], bytes]:
    left, top, right, bottom = (round(edge) for edge in font.getbbox(symbol))
    image = Image.new("L", (max(right - left, 1), max(bottom - top, 1)))
    ImageDraw.Draw(image).text((-left, -top), symbol, font=font, fill=255)
    return image.size, image.tobytes()


def _blend(fg: RGB, bg: RGB, share: float) -> RGB:
    return typing.cast("RGB", tuple(round(b + (f - b) * share) for f, b in zip(fg, bg)))


class FrameDrawer:
    """Draw frames onto one image, redrawing only the cells that changed."""

    def __init__(self, fonts: Fonts, width: int, height: int) -> None:
        """Create a blank image for a canvas of `width` by `height` cells, with half a line of padding."""
        self.fonts = fonts
        self.padding = fonts.cell_height // 2
        size = (width * fonts.cell_width + 2 * self.padding, height * fonts.cell_height + 2 * self.padding)
        self.image = Image.new("RGB", size, BACKGROUND)
        self._draw = ImageDraw.Draw(self.image)
        self._previous: list[tuple[Cell, ...]] | None = None

    def draw(self, rows: list[tuple[Cell, ...]]) -> bool:
        """Draw `rows`, returning whether any cell changed since the previous frame."""
        changed = False
        for y, row in enumerate(rows):
            previous = self._previous[y] if self._previous is not None else None
            if previous is row:
                continue
            for x, cell in enumerate(row):
                if previous is not None and previous[x] == cell:
                    continue
                changed = True
                # The cell after a wide symbol is drawn with it.
                if cell.symbol:
                    self._draw_cell(x, y, cell, wide=x + 1 < len(row) and not row[x + 1].symbol)
        self._previous = rows
        return changed

    def _draw_cell(self, x: int, y: int, cell: Cell, *, wide: bool) -> None:
        fonts = self.fonts
        fg, bg = (cell.bg, cell.fg) if cell.attributes & REVERSE else (cell.fg, cell.bg)
        if cell.attributes & DIM:
            fg = _blend(fg, bg, 1 / 2)
        left, top = self.padding + x * fonts.cell_width, self.padding + y * fonts.cell_height
        span = fonts.cell_width * (2 if wide else 1)
        right, bottom = left + span - 1, top + fonts.cell_height - 1
        symbol = cell.symbol
        if symbol in SHADES:
            self._draw.rectangle((left, top, right, bottom), fill=_blend(fg, bg, SHADES[symbol]))
            return
        self._draw.rectangle((left, top, right, bottom), fill=bg)
        if cell.attributes & HIDDEN:
            return
        if symbol in BLOCKS:
            x0, y0, x1, y1 = BLOCKS[symbol]
            box = (
                left + round(x0 * span),
                top + round(y0 * fonts.cell_height),
                left + round(x1 * span) - 1,
                top + round(y1 * fonts.cell_height) - 1,
            )
            self._draw.rectangle(box, fill=fg)
        elif symbol != " ":
            font = fonts.for_symbol(symbol, fonts.face(cell.attributes))
            offset = (span - font.getlength(symbol)) / 2
            self._draw.text((left + offset, top + fonts.baseline), symbol, font=font, fill=fg, anchor="ls")
        if cell.attributes & UNDERLINE:
            self._draw.line((left, top + fonts.baseline + 2, right, top + fonts.baseline + 2), fill=fg)
        if cell.attributes & STRIKE:
            middle = top + fonts.baseline - fonts.size // 3
            self._draw.line((left, middle, right, middle), fill=fg)


def frame_times(frame_count: int, frame_rate: int, fps: int, start_hold: float) -> Iterator[tuple[int, int]]:
    """Yield the index and start time in milliseconds of each recorded frame shown at up to `fps` frames per second.

    When `fps` is below the recording's frame rate, frames are skipped evenly. Every frame after the first starts
    `start_hold` seconds later, so the first frame is held that long.
    """
    period = 1 / min(fps, frame_rate)
    next_time = 0.0
    for index in range(frame_count):
        time = index / frame_rate
        if time + 1e-9 < next_time:
            continue
        next_time += period
        yield index, round(((time + start_hold) if index else 0.0) * 1000)


def render_webp(
    recording: Path,
    output: Path,
    *,
    fps: int,
    encoding: Encoding = LOSSLESS,
    fonts: Fonts | None = None,
    start_hold: float = 0.0,
    end_hold: float = 2.0,
) -> None:
    """Render `recording` to the animated WebP `output` at up to `fps` frames per second.

    The first frame is held for `start_hold` extra seconds and the last for `end_hold` seconds before the animation
    repeats.

    Raises:
        RenderError: If the font cannot be loaded, the recording has no frames, or `img2webp` fails.

    """
    fonts = fonts or Fonts(FONT)
    with RecordingReader(recording) as reader, tempfile.TemporaryDirectory(prefix="tte-webp-") as folder:
        work = Path(folder)
        header = reader.header
        drawer = FrameDrawer(fonts, header.width, header.height)
        frames: list[tuple[str, int]] = []

        def add(frame: str, start: int) -> None:
            if drawer.draw(parse_frame(frame, header.width, header.height)) or not frames:
                name = f"{len(frames):06d}.png"
                drawer.image.save(work / name, compress_level=1)
                frames.append((name, start))

        wanted = frame_times(sys.maxsize, header.frame_rate, fps, start_hold)
        index, start = next(wanted)
        last, skipped = -1, ""
        for last, frame in enumerate(reader.frames()):
            if last != index:
                skipped = frame
                continue
            add(frame, start)
            skipped = ""
            index, start = next(wanted)
        # Frames skipped to lower the frame rate never include the last, which shows the finished effect.
        if skipped:
            add(skipped, round((last / header.frame_rate + start_hold) * 1000))
        if not frames:
            message = f"{recording} has no frames."
            raise RenderError(message)
        end = round(((last + 1) / header.frame_rate + start_hold + end_hold) * 1000)
        _encode(work, frames, end, encoding)
        shutil.move(work / "out.webp", output)


def _encode(work: Path, frames: list[tuple[str, int]], end: int, encoding: Encoding) -> None:
    """Encode the frame images in `work` to `work/out.webp`, each shown until the next one starts."""
    arguments = encoding.file_options()
    for (name, start), (_, following) in zip(frames, [*frames[1:], ("", end)]):
        arguments += ["-d", str(following - start), "-lossless", name]
    # File names are relative to `work`, so the argument file needs no quoting.
    (work / "arguments.txt").write_text(" ".join([*arguments, "-o", "out.webp"]), encoding="utf-8")
    executable = shutil.which("img2webp")
    if executable is None:
        message = "img2webp from libwebp is not installed or not on PATH."
        raise RenderError(message)
    result = subprocess.run(  # noqa: S603 - Separated arguments; no shell.
        [executable, "arguments.txt"],
        check=False,
        cwd=work,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        message = f"img2webp exited with {result.returncode}: {(result.stderr or result.stdout).strip()}"
        raise RenderError(message)
