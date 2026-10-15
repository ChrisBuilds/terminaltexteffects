"""Draw recordings as animated GIF or WebP images with Pillow.

Each frame is drawn cell by cell in a monospace font, with the colors and attributes of the recorded ANSI sequences.
Only cells that changed since the previous frame are redrawn, and frames identical to the one before are merged into
a longer frame. Frames are kept as temporary PNG files, so memory use does not grow with the recording's length.

WebP output is lossless. GIF output maps every frame to one palette of up to 255 colors sampled from the frames, and
stores only the changed area of each frame, with unchanged pixels inside it transparent.

Block elements are drawn as filled rectangles and shades as blended colors, so they tile without gaps as they do
in most terminals. Symbols the main font lacks, such as the half-width katakana in `matrix`, are drawn with the
first fallback font that has them.

This module needs Pillow, which `terminaltexteffects.utils.export` imports only when exporting.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import typing
from dataclasses import dataclass
from functools import cache, lru_cache
from pathlib import Path

from PIL import GifImagePlugin, Image, ImageChops, ImageDraw, ImageFont

from terminaltexteffects.engine._recording import RecordingReader
from terminaltexteffects.utils.hexterm import xterm_to_hex
from terminaltexteffects.utils.terminal_text import get_symbol_cell_width

if typing.TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

RGB = tuple[int, int, int]

BACKGROUND: RGB = (0x12, 0x13, 0x14)
"""The background color, from the `asciinema` terminal theme."""

FOREGROUND: RGB = (0xCC, 0xCC, 0xCC)
"""The default text color, from the `asciinema` terminal theme."""

FONT_SIZE = 14
LINE_HEIGHT = 1.4
"""Font size in pixels and line height in font sizes."""

FontFace = tuple[str, int]
"""A font file name or path, and the index of the face in a font collection."""

MONOSPACE_FONTS: tuple[tuple[FontFace, FontFace, FontFace, FontFace], ...] = (
    (
        ("DejaVuSansMono.ttf", 0),
        ("DejaVuSansMono-Bold.ttf", 0),
        ("DejaVuSansMono-Oblique.ttf", 0),
        ("DejaVuSansMono-BoldOblique.ttf", 0),
    ),
    (("Menlo.ttc", 0), ("Menlo.ttc", 1), ("Menlo.ttc", 2), ("Menlo.ttc", 3)),
    (("consola.ttf", 0), ("consolab.ttf", 0), ("consolai.ttf", 0), ("consolaz.ttf", 0)),
    (
        ("LiberationMono-Regular.ttf", 0),
        ("LiberationMono-Bold.ttf", 0),
        ("LiberationMono-Italic.ttf", 0),
        ("LiberationMono-BoldItalic.ttf", 0),
    ),
)
"""Monospace fonts tried in order when no font is given, each as its regular, bold, italic, and bold italic faces.

Font file names are found in the system font folders. DejaVu Sans Mono comes with most Linux systems, Menlo with
macOS, and Consolas with Windows.
"""

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
    """Raised when a recording cannot be drawn as an animation."""


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


class Fonts:
    """The main font in each face, and fallback fonts for symbols it lacks."""

    def __init__(self, font: str | None = None, fallbacks: Sequence[str] = (), size: int = FONT_SIZE) -> None:
        """Load `font`, a path or a font file name in the system font folders, and its bold and oblique faces.

        Faces beside `font` named with `-Bold`, `-Oblique`, and `-BoldOblique` are used when they exist; otherwise
        every face is drawn with `font`. Without `font`, the first installed font in `MONOSPACE_FONTS` is used, or the
        monospace font `fontconfig` picks. `fallbacks` are tried before `FALLBACK_FONTS` for missing symbols.

        Raises:
            RenderError: If no font can be found or loaded.

        """
        self.size = size
        if font is None:
            self.regular, self.faces = _system_font(size)
        else:
            try:
                self.regular = ImageFont.truetype(font, size)
            except OSError as error:
                message = f"Cannot load the font {font!r} ({error})."
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
        self.missing: set[str] = set()
        """Symbols no font has, drawn with the main font's missing-glyph box."""

    def face(self, attributes: int) -> ImageFont.FreeTypeFont:
        """Return the main font face for the bold and italic `attributes`."""
        return self.faces.get(attributes & (BOLD | ITALIC), self.regular)

    def for_symbol(self, symbol: str, face: ImageFont.FreeTypeFont) -> ImageFont.FreeTypeFont:
        """Return `face` when it has `symbol`, otherwise the first fallback font that has it."""
        if _has_glyph(face, symbol):
            return face
        fallback = self._fallback(symbol)
        if fallback is None:
            self.missing.add(symbol)
            return face
        return fallback

    def _fallback(self, symbol: str) -> ImageFont.FreeTypeFont | None:
        for name in [*_fontconfig_match(f"monospace:charset={ord(symbol):x}"), *self.fallback_names]:
            font = _load_font(name, 0, self.size)
            if font is not None and _has_glyph(font, symbol):
                return font
        return None


def _system_font(size: int) -> tuple[ImageFont.FreeTypeFont, dict[int, ImageFont.FreeTypeFont]]:
    """Return the first installed font in `MONOSPACE_FONTS`, or `fontconfig`'s monospace font, and its faces.

    Raises:
        RenderError: If no monospace font is found.

    """
    for regular_face, *styled_faces in MONOSPACE_FONTS:
        regular = _load_font(*regular_face, size)
        if regular is None:
            continue
        faces = {}
        for attributes, styled_face in zip((BOLD, ITALIC, BOLD | ITALIC), styled_faces):
            faces[attributes] = _load_font(*styled_face, size) or regular
        return regular, faces
    for name in _fontconfig_match("monospace"):
        regular = _load_font(name, 0, size)
        if regular is not None:
            return regular, {}
    message = "No monospace font was found; install DejaVu Sans Mono."
    raise RenderError(message)


@cache
def _load_font(name: str, index: int, size: int) -> ImageFont.FreeTypeFont | None:
    try:
        return ImageFont.truetype(name, size, index=index)
    except OSError:
        return None


@cache
def _fontconfig_match(pattern: str) -> tuple[str, ...]:
    """Return the font file `fontconfig` picks for `pattern`, when `fc-match` is installed."""
    executable = shutil.which("fc-match")
    if executable is None:
        return ()
    try:
        result = subprocess.run(  # noqa: S603 - Separated arguments; no shell.
            [executable, "-f", "%{file}", pattern],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return ()
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


@dataclass(frozen=True)
class Frames:
    """Frames drawn from a recording, saved as PNG files: each file and its start time in milliseconds.

    `end` is when the recording ends, in milliseconds, and `missing` holds the symbols no font has.
    """

    paths: list[Path]
    starts: list[int]
    end: int
    size: tuple[int, int]
    missing: frozenset[str]


def draw_frames(recording: Path, folder: Path, *, fps: int, fonts: Fonts, start_hold: float = 0.0) -> Frames:
    """Draw `recording` at up to `fps` frames per second, saving each distinct frame as a PNG file in `folder`.

    The first frame is held for `start_hold` extra seconds.

    Raises:
        RenderError: If the recording has no frames.

    """
    with RecordingReader(recording) as reader:
        header = reader.header
        drawer = FrameDrawer(fonts, header.width, header.height)
        paths: list[Path] = []
        starts: list[int] = []

        def add(frame: str, start: int) -> None:
            if drawer.draw(parse_frame(frame, header.width, header.height)) or not paths:
                path = folder / f"{len(paths):06d}.png"
                drawer.image.save(path, compress_level=1)
                paths.append(path)
                starts.append(start)

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
    if not paths:
        message = f"{recording} has no frames."
        raise RenderError(message)
    end = round(((last + 1) / header.frame_rate + start_hold) * 1000)
    return Frames(paths, starts, end, drawer.image.size, frozenset(fonts.missing))


class _FrameFiles(Image.Image):
    """A multi-frame image that loads each frame from its file when Pillow seeks to it, holding one at a time."""

    def __init__(self, paths: Sequence[Path], size: tuple[int, int]) -> None:
        super().__init__()
        self._paths = paths
        self._mode = "RGB"
        self._size = size
        self.n_frames = len(paths)
        self._index = -1
        self.seek(0)

    def seek(self, frame: int) -> None:
        if frame != self._index:
            with Image.open(self._paths[frame]) as image:
                self.im = image.convert("RGB").im
            self._index = frame

    def tell(self) -> int:
        return self._index


def write_webp(frames: Frames, output: Path, *, end_hold: float = 2.0, minimize_size: bool = False) -> None:
    """Write `frames` to the lossless animated WebP `output`, holding the last frame for `end_hold` seconds.

    `minimize_size` makes the file a few percent smaller, at about three times the encoding time.
    """
    ends = [*frames.starts[1:], frames.end + round(end_hold * 1000)]
    durations = [end - start for start, end in zip(frames.starts, ends)]
    _FrameFiles(frames.paths, frames.size).save(
        output,
        format="WEBP",
        save_all=True,
        duration=durations,
        loop=0,
        lossless=True,
        quality=75,
        method=4,
        minimize_size=minimize_size,
    )


GIF_MAX_FPS = 50
"""The highest frame rate a GIF plays, since browsers slow frames shorter than two hundredths of a second."""

GIF_MIN_DELAY = 2
"""The shortest GIF frame delay, in hundredths of a second, that browsers play as written."""

PALETTE_PIXELS = 16_000_000
"""The most pixels sampled from the frames to choose a GIF's palette."""

PALETTE_SAMPLES = 64
"""The most frames sampled to choose a GIF's palette."""


def gif_delays(starts: Sequence[int], end: int) -> list[tuple[int, int]]:
    """Return the index and delay in hundredths of a second of each frame shown, from start times in milliseconds.

    Start times are rounded to multiples of `GIF_MIN_DELAY`. A frame rounded to the same start as the frame before
    replaces it, so frames recorded faster than `GIF_MAX_FPS` are skipped evenly and none plays slower than written.
    """
    kept: list[list[int]] = []
    for index, start in enumerate(starts):
        centiseconds = _gif_time(start)
        if kept and centiseconds <= kept[-1][1]:
            kept[-1][0] = index
        else:
            kept.append([index, centiseconds])
    ends = [start for _, start in kept[1:]] + [max(_gif_time(end), kept[-1][1] + GIF_MIN_DELAY)]
    return [(index, following - start) for (index, start), following in zip(kept, ends)]


def _gif_time(milliseconds: int) -> int:
    """Return `milliseconds` in hundredths of a second, rounded to a multiple of `GIF_MIN_DELAY`."""
    return round(milliseconds / (10 * GIF_MIN_DELAY)) * GIF_MIN_DELAY


def gif_palette(images: Sequence[Image.Image]) -> list[int]:
    """Return one palette of up to 255 colors for `images`, as a flat list of red, green, and blue values.

    When the images hold 255 colors or fewer, the palette has exactly those colors.
    """
    width, height = images[0].size
    sheet = Image.new("RGB", (width, height * len(images)))
    for row, image in enumerate(images):
        sheet.paste(image, (0, row * height))
    colors = sheet.getcolors(255)
    if colors is not None:
        return [value for _, color in colors for value in typing.cast("RGB", color)]
    quantized = sheet.quantize(255, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    return (quantized.getpalette() or [])[: 255 * 3]


def _palette_samples(frames: Frames, indices: Sequence[int]) -> list[Image.Image]:
    """Return evenly spaced frames from `indices`, including the last, which shows the finished effect."""
    width, height = frames.size
    count = max(1, min(PALETTE_SAMPLES, PALETTE_PIXELS // (width * height), len(indices)))
    chosen = sorted({indices[round(step * (len(indices) - 1) / max(count - 1, 1))] for step in range(count)})
    samples = []
    for index in chosen:
        with Image.open(frames.paths[index]) as image:
            samples.append(image.convert("RGB"))
    return samples


def write_gif(frames: Frames, output: Path, *, end_hold: float = 2.0) -> None:
    """Write `frames` to the animated GIF `output`, holding the last frame for `end_hold` seconds.

    Every frame is mapped to one palette, without dithering. After the first frame, each frame stores only the area
    that changed, with unchanged pixels inside it transparent, and is drawn over the frame before.
    """
    delays = gif_delays(frames.starts, frames.end + round(end_hold * 1000))
    palette = gif_palette(_palette_samples(frames, [index for index, _ in delays]))
    transparent = len(palette) // 3
    palette_image = Image.new("P", (1, 1))
    palette_image.putpalette(palette)
    canvas = Image.new("P", frames.size)
    canvas.putpalette([*palette, 0, 0, 0])
    header, _ = GifImagePlugin.getheader(canvas, info={"loop": 0, "transparency": transparent})
    with output.open("wb") as file:
        file.writelines(header)
        previous: Image.Image | None = None
        pending: tuple[Image.Image, tuple[int, int], int] | None = None
        for index, delay in delays:
            with Image.open(frames.paths[index]) as image:
                indices = image.convert("RGB").quantize(palette=palette_image, dither=Image.Dither.NONE)
            current = Image.frombytes("L", frames.size, indices.tobytes())
            if previous is None:
                piece, offset = current, (0, 0)
            else:
                difference = ImageChops.difference(current, previous)
                box = difference.getbbox()
                if box is None:
                    # Mapping to the palette can make different frames identical.
                    assert pending is not None
                    pending = (pending[0], pending[1], pending[2] + delay)
                    continue
                piece = current.crop(box)
                piece.paste(transparent, mask=difference.crop(box).point(lambda value: 0 if value else 255))
                offset = box[:2]
            if pending is not None:
                _write_gif_frame(file, *pending, transparent)
            pending = (piece, offset, delay)
            previous = current
        assert pending is not None
        _write_gif_frame(file, *pending, transparent)
        file.write(b";")


def _write_gif_frame(
    file: typing.BinaryIO,
    indices: Image.Image,
    offset: tuple[int, int],
    delay: int,
    transparent: int,
) -> None:
    """Write one frame of palette `indices` at `offset`, shown for `delay` hundredths of a second."""
    frame = Image.frombytes("P", indices.size, indices.tobytes())
    file.writelines(
        GifImagePlugin.getdata(frame, offset, duration=delay * 10, disposal=1, transparency=transparent),
    )
