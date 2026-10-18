"""Render the concept diagrams for the 3D Effects part of the Effect Guide.

These are drawings, not TTE output: smooth lines and shapes that explain an idea (a camera, a projection, a turn)
before the guide shows what it looks like in cells. The 3D math comes from `terminaltexteffects.utils.geometry3d`,
so the diagrams follow the same conventions as the engine: x right, y up, z toward the viewer.

Requires Pillow, installed on Python 3.10 and later by `uv sync --group dev`.

Examples:
    ./.venv/bin/python tools/render_3d_diagrams.py --list
    ./.venv/bin/python tools/render_3d_diagrams.py
    ./.venv/bin/python tools/render_3d_diagrams.py projection lambert

"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from terminaltexteffects.utils import geometry3d as g3
from terminaltexteffects.utils.geometry3d import Rotation, Vec3

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "docs" / "img" / "effectguide" / "3d"

SUPERSAMPLE = 3
"""Diagrams are drawn this many times larger and scaled down, which smooths their edges."""

FRAME_MS = 40
"""Animated diagrams play at 25 frames per second, which keeps them small and is smooth enough for slow motion."""

BACKGROUND = (18, 19, 20)
TEXT = (220, 222, 228)
MUTED = (130, 134, 145)
FAINT = (60, 63, 70)
PURPLE = (138, 0, 138)
CYAN = (0, 209, 255)
WHITE = (255, 255, 255)
RED = (255, 95, 95)
GREEN = (95, 255, 135)
BLUE = (95, 175, 255)
AMBER = (255, 190, 60)

Point = tuple[float, float]
RGB = tuple[int, int, int]

FONT_CANDIDATES = (
    "Inter-Regular.otf",
    "/usr/share/fonts/opentype/inter/Inter-Regular.otf",
    "DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "C:/Windows/Fonts/arial.ttf",
)
MONO_CANDIDATES = (
    "DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "Menlo.ttc",
    "/System/Library/Fonts/Menlo.ttc",
    "C:/Windows/Fonts/consola.ttf",
)


def load_font(candidates: Sequence[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Return the first font that loads at `size` pixels, or Pillow's built-in font."""
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:  # noqa: PERF203 - Runs once per font, and bare names need Pillow's own search.
            continue
    return ImageFont.load_default(size)


def mix(a: RGB, b: RGB, t: float) -> RGB:
    """Return the color `t` of the way from `a` to `b`."""
    t = min(max(t, 0.0), 1.0)
    return (round(a[0] + (b[0] - a[0]) * t), round(a[1] + (b[1] - a[1]) * t), round(a[2] + (b[2] - a[2]) * t))


def shade(t: float) -> RGB:
    """Return the brand gradient (purple, cyan, white) at `t` from 0 to 1, the colors `Shaded()` uses."""
    return mix(PURPLE, CYAN, t * 2) if t < 0.5 else mix(CYAN, WHITE, t * 2 - 1)


class Canvas:
    """One frame of a diagram, drawn at `SUPERSAMPLE` times its size. Coordinates are in output pixels."""

    def __init__(self, width: int, height: int) -> None:
        """Start a blank frame `width` by `height` pixels."""
        self.width, self.height = width, height
        self.image = Image.new("RGB", (width * SUPERSAMPLE, height * SUPERSAMPLE), BACKGROUND)
        self.draw = ImageDraw.Draw(self.image)
        self._fonts: dict[tuple[bool, int], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}

    def _s(self, point: Point) -> Point:
        return (point[0] * SUPERSAMPLE, point[1] * SUPERSAMPLE)

    def font(self, size: int, *, mono: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """Return the text or monospace font at `size` output pixels."""
        key = (mono, size)
        if key not in self._fonts:
            self._fonts[key] = load_font(MONO_CANDIDATES if mono else FONT_CANDIDATES, size * SUPERSAMPLE)
        return self._fonts[key]

    def line(self, a: Point, b: Point, color: RGB, width: float = 2, *, dash: float = 0) -> None:
        """Draw a line, solid or dashed with `dash` pixel segments."""
        if not dash:
            self.draw.line([self._s(a), self._s(b)], fill=color, width=round(width * SUPERSAMPLE))
            return
        length = math.dist(a, b)
        steps = max(1, int(length // (dash * 2)))
        for step in range(steps + 1):
            start = step * dash * 2 / length if length else 0
            end = min(1.0, start + dash / length) if length else 0
            if start >= 1:
                break
            p = (a[0] + (b[0] - a[0]) * start, a[1] + (b[1] - a[1]) * start)
            q = (a[0] + (b[0] - a[0]) * end, a[1] + (b[1] - a[1]) * end)
            self.draw.line([self._s(p), self._s(q)], fill=color, width=round(width * SUPERSAMPLE))

    def arrow(self, a: Point, b: Point, color: RGB, width: float = 2, head: float = 9, *, dash: float = 0) -> None:
        """Draw a line from `a` to `b` with an arrowhead at `b`."""
        angle = math.atan2(b[1] - a[1], b[0] - a[0])
        back = (b[0] - head * 0.8 * math.cos(angle), b[1] - head * 0.8 * math.sin(angle))
        self.line(a, back, color, width, dash=dash)
        left = (b[0] - head * math.cos(angle - 0.45), b[1] - head * math.sin(angle - 0.45))
        right = (b[0] - head * math.cos(angle + 0.45), b[1] - head * math.sin(angle + 0.45))
        self.polygon([b, left, right], color)

    def polygon(self, points: Sequence[Point], fill: RGB | None, outline: RGB | None = None, width: float = 2) -> None:
        """Fill a polygon, and outline it if `outline` is given."""
        scaled = [self._s(point) for point in points]
        self.draw.polygon(scaled, fill=fill)
        if outline is not None:
            self.draw.line([*scaled, scaled[0]], fill=outline, width=round(width * SUPERSAMPLE), joint="curve")

    def rect(
        self, left: float, top: float, right: float, bottom: float, fill: RGB | None, outline: RGB | None = None
    ) -> None:
        """Fill a rectangle, and outline it if `outline` is given."""
        self.polygon([(left, top), (right, top), (right, bottom), (left, bottom)], fill, outline, 1)

    def circle(
        self, center: Point, radius: float, fill: RGB | None, outline: RGB | None = None, width: float = 2
    ) -> None:
        """Fill a circle, and outline it if `outline` is given."""
        x, y = self._s(center)
        r = radius * SUPERSAMPLE
        self._check((x - r, y - r, x + r, y + r), f"circle at {center}")
        self.draw.ellipse([x - r, y - r, x + r, y + r], fill=fill, outline=outline, width=round(width * SUPERSAMPLE))

    def arc(self, center: Point, radius: float, start: float, end: float, color: RGB, width: float = 2) -> None:
        """Draw an arc from `start` to `end` degrees, measured clockwise from the +x direction on screen."""
        x, y = self._s(center)
        r = radius * SUPERSAMPLE
        self.draw.arc([x - r, y - r, x + r, y + r], start, end, fill=color, width=round(width * SUPERSAMPLE))

    def text(
        self,
        point: Point,
        text: str,
        color: RGB = TEXT,
        size: int = 14,
        anchor: str = "mm",
        *,
        mono: bool = False,
    ) -> None:
        """Draw `text` positioned by its `anchor`, a Pillow anchor such as `"mm"` for its middle."""
        font = self.font(size, mono=mono)
        self._check(self.draw.textbbox(self._s(point), text, font=font, anchor=anchor), repr(text))
        self.draw.text(self._s(point), text, fill=color, font=font, anchor=anchor)

    def _check(self, box: tuple[float, float, float, float], what: str) -> None:
        """Record `what` if its supersampled bounding `box` reaches past the frame."""
        left, top, right, bottom = box
        if left < 0 or top < 0 or right > self.image.width or bottom > self.image.height:
            CLIPPED.add(what)

    def finish(self) -> Image.Image:
        """Return the frame scaled down to its output size."""
        return self.image.resize((self.width, self.height), Image.Resampling.LANCZOS)


@dataclass
class View:
    """An illustration camera: turns world points by `yaw` and `pitch`, then maps them to pixels around `center`.

    `distance` adds a mild perspective; `None` draws without one.
    """

    center: Point
    scale: float
    yaw: float = -30.0
    pitch: float = 20.0
    distance: float | None = None

    def turn(self) -> Rotation:
        """Return the rotation from world to view."""
        return Rotation.about_x(math.radians(self.pitch)) * Rotation.about_y(math.radians(self.yaw))

    def depth(self, point: Vec3) -> float:
        """Return how far toward the viewer `point` is. Larger is nearer."""
        return self.turn().apply(point).z

    def __call__(self, point: Vec3) -> Point:
        """Return the pixel `point` is drawn at."""
        p = self.turn().apply(point)
        factor = 1.0 if self.distance is None else self.distance / (self.distance - p.z)
        return (self.center[0] + p.x * self.scale * factor, self.center[1] - p.y * self.scale * factor)


SOLID_LIGHT = Vec3(-0.5, 0.6, 1.0)
"""The direction toward the light that `solid` shades faces by."""


def solid(
    canvas: Canvas,
    view: View,
    mesh: g3.Mesh,
    rotation: Rotation,
    *,
    position: Vec3 = g3.ORIGIN,
    light: Vec3 = SOLID_LIGHT,
    colors: Callable[[int, float], RGB] | None = None,
    outline: RGB | None = None,
) -> None:
    """Draw a convex mesh with flat shading, skipping faces turned away from the view."""
    world = g3.transform_points(mesh.vertices, rotation, position=position)
    turn = view.turn()
    for face, normal in zip(mesh.faces, mesh.normals):
        turned = rotation.apply(normal)
        if turn.apply(turned).z <= 0:
            continue
        lit = 0.15 + 0.85 * g3.lambert(turned, light)
        fill = colors(face.tag, lit) if colors else shade(lit)
        canvas.polygon([view(world[i]) for i in face.indices], fill, outline or mix(fill, BACKGROUND, 0.35), 1.5)


def save(name: str, frames: list[Image.Image], out_dir: Path) -> Path:
    """Save one frame as a still WebP, or several as a looping animation."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.webp"
    if len(frames) == 1:
        frames[0].save(path, lossless=True, method=6)
    else:
        frames[0].save(
            path, save_all=True, append_images=frames[1:], duration=FRAME_MS, loop=0, lossless=True, method=4
        )
    return path


def ease(t: float) -> float:
    """Ease in and out, for diagram motion."""
    return 0.5 - 0.5 * math.cos(math.pi * t)


# Diagrams. Each returns its frames.


def cell_sampling() -> list[Image.Image]:
    """Show a smooth shape, the cells whose centers it covers, and an edge drawn one cell per step."""
    canvas = Canvas(780, 300)
    cell_w, cell_h = 12, 24
    columns, rows = 16, 8
    corners = [(1.5, 3.5), (8.5, 0.6), (14.5, 4.2), (7.2, 7.4)]

    def to_px(origin: Point, x: float, y: float) -> Point:
        return (origin[0] + x * cell_w, origin[1] + y * cell_h)

    def inside(x: float, y: float) -> bool:
        sign = None
        for (ax, ay), (bx, by) in zip(corners, corners[1:] + corners[:1]):
            cross = (bx - ax) * (y - ay) - (by - ay) * (x - ax)
            if sign is None:
                sign = cross > 0
            elif (cross > 0) != sign:
                return False
        return True

    titles = ("The shape", "Filled: every cell whose center it covers", "Edges: one cell per step")
    for panel, title in enumerate(titles):
        origin = (20 + panel * 255, 60)
        canvas.text((origin[0] + columns * cell_w / 2, 30), title, TEXT, 13)
        for column in range(columns + 1):
            canvas.line(to_px(origin, column, 0), to_px(origin, column, rows), FAINT, 1)
        for row in range(rows + 1):
            canvas.line(to_px(origin, 0, row), to_px(origin, columns, row), FAINT, 1)
        if panel == 1:
            for column in range(columns):
                for row in range(rows):
                    if inside(column + 0.5, row + 0.5):
                        x0, y0 = to_px(origin, column, row)
                        canvas.rect(x0 + 1, y0 + 1, x0 + cell_w - 1, y0 + cell_h - 1, CYAN)
        if panel == 2:
            for (ax, ay), (bx, by) in zip(corners, corners[1:] + corners[:1]):
                steps = int(max(abs(bx - ax), abs(by - ay)) * 2)
                seen = set()
                for step in range(steps + 1):
                    t = step / steps
                    cell = (int(ax + (bx - ax) * t), int(ay + (by - ay) * t))
                    if cell in seen:
                        continue
                    seen.add(cell)
                    x0, y0 = to_px(origin, *cell)
                    canvas.rect(x0 + 1, y0 + 1, x0 + cell_w - 1, y0 + cell_h - 1, PURPLE)
        outline = [to_px(origin, x, y) for x, y in corners]
        canvas.polygon(outline, None, WHITE if panel == 0 else mix(WHITE, BACKGROUND, 0.4), 2)
    canvas.text(
        (390, 275),
        "Each cell shows one symbol. A filled face keeps its area; a thin edge becomes a staircase.",
        MUTED,
        13,
    )
    return [canvas.finish()]


def world_axes() -> list[Image.Image]:
    """Show the world axes, the canvas on the z = 0 plane, and the camera out on +z, from a moving viewpoint."""
    frames = []
    count = 100
    for index in range(count):
        t = index / count
        # Sized so the camera, its label and the axis labels stay inside the image through the whole sweep.
        view = View((390, 200), 2.7, yaw=-40 + 30 * math.sin(2 * math.pi * t), pitch=18, distance=400)
        canvas = Canvas(720, 400)
        # The canvas: a rectangle on the z = 0 plane with a few rows of text.
        w, h = 40, 24
        corners = [Vec3(-w, -h, 0), Vec3(w, -h, 0), Vec3(w, h, 0), Vec3(-w, h, 0)]
        canvas.polygon([view(c) for c in corners], (30, 32, 38), FAINT, 1.5)
        for row in range(-2, 3):
            y = row * 6.0
            canvas.line(view(Vec3(-22, y, 0)), view(Vec3(22, y, 0)), mix(TEXT, BACKGROUND, 0.55), 3)
        canvas.text(view(Vec3(-w + 2, h + 4, 0)), "canvas (z = 0)", MUTED, 12, "lm")
        # The camera on +z, looking at the origin.
        eye = Vec3(0, 0, 110)
        for corner in corners:
            canvas.line(view(eye), view(corner), FAINT, 1, dash=4)
        canvas.circle(view(eye), 7, AMBER)
        canvas.text((view(eye)[0], view(eye)[1] - 20), "camera", AMBER, 13)
        # Axes, drawn far to near so nearer ones cover farther ones.
        axes = [
            (Vec3(52, 0, 0), RED, "+x right"),
            (Vec3(0, 36, 0), GREEN, "+y up"),
            (Vec3(0, 0, 70), BLUE, "+z toward you"),
        ]
        axes.sort(key=lambda item: view.depth(item[0]))
        for tip, color, label in axes:
            canvas.arrow(view(g3.ORIGIN), view(tip), color, 3, 12)
            end = view(tip * 1.12)
            canvas.text(end, label, color, 13)
        canvas.circle(view(g3.ORIGIN), 4, WHITE)
        canvas.text((view(g3.ORIGIN)[0] - 12, view(g3.ORIGIN)[1] - 14), "origin: canvas center", TEXT, 12, "rm")
        frames.append(canvas.finish())
    return frames


def tall_cells() -> list[Image.Image]:
    """One cell's shape, and a square drawn without and with the row correction."""
    canvas = Canvas(780, 330)
    cell_w, cell_h = 14, 28
    # A single cell.
    canvas.text((80, 40), "One cell", TEXT, 14)
    canvas.rect(66, 90, 66 + cell_w * 2, 90 + cell_h * 2, (30, 32, 38), MUTED)
    canvas.text((80, 90 + cell_h * 2 + 22), "1 wide", MUTED, 12)
    canvas.text((80, 90 + cell_h * 2 + 38), "about 2 tall", MUTED, 12)

    def grid(origin: Point, columns: int, rows: int, filled: Callable[[int, int], bool], color: RGB) -> None:
        for column in range(columns):
            for row in range(rows):
                x0, y0 = origin[0] + column * cell_w, origin[1] + row * cell_h
                canvas.rect(x0, y0, x0 + cell_w, y0 + cell_h, color if filled(column, row) else None, FAINT)

    canvas.text((300, 40), "8 units, one cell per unit", TEXT, 14)
    grid((244, 60), 8, 8, lambda _c, _r: True, PURPLE)
    canvas.text((300, 60 + 8 * cell_h + 18), "8 columns by 8 rows: a tall box", MUTED, 12)
    canvas.text((560, 40), "8 units, rows counted as 2", TEXT, 14)
    grid((504, 60 + 2 * cell_h), 8, 4, lambda _c, _r: True, CYAN)
    canvas.text((560, 60 + 8 * cell_h + 18), "8 columns by 4 rows: a square", MUTED, 12)
    return [canvas.finish()]


def transform_order() -> list[Image.Image]:
    """Seen from above: turning before moving spins in place; moving before turning orbits the origin."""
    frames = []
    count = 120
    square = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    for index in range(count):
        angle = 2 * math.pi * index / count
        canvas = Canvas(760, 360)
        for panel, (title, orbit) in enumerate(
            (("Turn, then move: spins in place", False), ("Move, then turn: orbits", True))
        ):
            cx, cy = 190 + panel * 380, 200
            canvas.text((cx, 30), title, TEXT, 15)
            canvas.line((cx - 8, cy), (cx + 8, cy), MUTED, 1.5)
            canvas.line((cx, cy - 8), (cx, cy + 8), MUTED, 1.5)
            canvas.text((cx, cy + 22), "origin", MUTED, 11)
            offset = (100.0, 0.0)
            if orbit:
                canvas.circle((cx, cy), 100, None, FAINT, 1)
            else:
                canvas.line((cx, cy), (cx + offset[0], cy), FAINT, 1, dash=4)
            c, s = math.cos(angle), math.sin(angle)
            points = []
            for corner_x, corner_y in square:
                x, y = corner_x * 26, corner_y * 26
                if orbit:
                    x, y = x + offset[0], y + offset[1]
                    x, y = x * c - y * s, x * s + y * c
                else:
                    x, y = x * c - y * s, x * s + y * c
                    x, y = x + offset[0], y + offset[1]
                points.append((cx + x, cy - y))
            canvas.polygon(points, mix(CYAN, BACKGROUND, 0.25), WHITE, 1.5)
            # A dot on one corner shows the turn.
            canvas.circle(points[1], 5, AMBER)
        canvas.text((380, 340), "The same turn and the same move, applied in a different order.", MUTED, 13)
        frames.append(canvas.finish())
    return frames


def transform_pipeline() -> list[Image.Image]:
    """Show a body's points going from its own coordinates to the world: scale, then rotate, then move."""
    canvas = Canvas(860, 260)
    steps = [
        ("Body coordinates", 1.0, 0.0, (0.0, 0.0)),
        ("scale", 1.5, 0.0, (0.0, 0.0)),
        ("rotate", 1.5, 35.0, (0.0, 0.0)),
        ("move", 1.5, 35.0, (34.0, 22.0)),
    ]
    for index, (label, size, degrees, (dx, dy)) in enumerate(steps):
        cx, cy = 110 + index * 210, 140
        canvas.line((cx - 80, cy), (cx + 80, cy), FAINT, 1)
        canvas.line((cx, cy - 80), (cx, cy + 80), FAINT, 1)
        canvas.text((cx, 30), label, TEXT if index else MUTED, 15)
        view = View((cx + dx, cy - dy), 1.0, yaw=0, pitch=0)
        mesh = g3.box(26 * size, 26 * size, 26 * size)
        rotation = Rotation.about_z(math.radians(degrees))
        world = g3.transform_points(mesh.vertices, rotation)
        canvas.polygon([view(world[i]) for i in (0, 1, 2, 3)], mix(CYAN, BACKGROUND, 0.25), WHITE, 1.5)
        canvas.circle(view(world[1]), 4, AMBER)
        if index < len(steps) - 1:
            canvas.arrow((cx + 86, cy), (cx + 124, cy), MUTED, 2)
    canvas.text((430, 245), "Body.scale, Body.rotation and Body.position hold the three steps.", MUTED, 13)
    return [canvas.finish()]


def rotation_axes() -> list[Image.Image]:
    """Show a cube turning about x, y and z, each with its axis and the direction a positive angle turns."""
    frames = []
    count = 120
    mesh = g3.box(60, 60, 60)
    for index in range(count):
        angle = 2 * math.pi * index / count
        canvas = Canvas(840, 330)
        for panel, (name, color, axis) in enumerate(
            (("x", RED, g3.X_AXIS), ("y", GREEN, g3.Y_AXIS), ("z", BLUE, g3.Z_AXIS))
        ):
            view = View((140 + panel * 280, 170), 1.25, yaw=-30, pitch=20)
            canvas.text((140 + panel * 280, 26), f'spin("{name}") or rotate("{name}", degrees)', TEXT, 13, mono=True)
            start, end = view(axis * -78), view(axis * 78)
            # Draw the half of the axis that's farther away first, so the cube covers it.
            if view.depth(axis) < 0:
                canvas.arrow(view(g3.ORIGIN), end, color, 3, 12)
                solid(canvas, view, mesh, Rotation.about_axis(axis, angle))
                canvas.line(start, view(g3.ORIGIN), color, 3)
            else:
                canvas.line(start, view(g3.ORIGIN), color, 3)
                solid(canvas, view, mesh, Rotation.about_axis(axis, angle))
                canvas.arrow(view(g3.ORIGIN), end, color, 3, 12)
            canvas.text((end[0] + 14, end[1] - 8), f"+{name}", color, 14)
        canvas.text(
            (420, 310),
            "A positive angle turns counterclockwise when you look back along the axis from its + end.",
            MUTED,
            13,
        )
        frames.append(canvas.finish())
    return frames


def rotation_local() -> list[Image.Image]:
    """Show a tilted body spun about world y, where its axis sweeps a cone, beside one spun about its own y."""
    frames = []
    count = 120
    mesh = g3.box(44, 96, 44)
    tilt = Rotation.about_z(math.radians(-30))
    for index in range(count):
        turn = Rotation.about_y(2 * math.pi * index / count)
        canvas = Canvas(840, 360)
        panels = (
            ('spin("y")', "Turns about world y. Its own axis (amber) sweeps a cone.", turn * tilt),
            ('spin("y", local=True)', "Turns about its own axis (amber), which stays put.", tilt * turn),
        )
        for panel, (call, caption, pose) in enumerate(panels):
            center_x = 210 + panel * 420
            view = View((center_x, 185), 1.2, yaw=-30, pitch=18)
            canvas.text((center_x, 26), call, TEXT, 14, mono=True)
            canvas.text((center_x, 334), caption, MUTED, 13)
            canvas.line(view(g3.Y_AXIS * -100), view(g3.Y_AXIS * 100), FAINT, 2)
            canvas.text(view(g3.Y_AXIS * 112), "world y", MUTED, 12)
            if panel == 0:
                # The path the body's axis tip sweeps while the body turns about world y.
                path = [
                    view(Rotation.about_y(2 * math.pi * k / 48).apply(tilt.apply(g3.Y_AXIS * 84))) for k in range(49)
                ]
                for a, b in zip(path, path[1:]):
                    canvas.line(a, b, mix(BACKGROUND, AMBER, 0.45), 1.5)
            axis = pose.apply(g3.Y_AXIS)
            end = view(axis * 84)
            # Only the parts that stick out of the body's ends show. Draw the farther one first, so the body covers it.
            if view.depth(axis) < 0:
                canvas.arrow(view(axis * 48), end, AMBER, 3, 12)
                solid(canvas, view, mesh, pose)
                canvas.line(view(axis * -84), view(axis * -48), AMBER, 3)
            else:
                canvas.line(view(axis * -84), view(axis * -48), AMBER, 3)
                solid(canvas, view, mesh, pose)
                canvas.arrow(view(axis * 48), end, AMBER, 3, 12)
        frames.append(canvas.finish())
    return frames


def rotation_order() -> list[Image.Image]:
    """Show that turning 90 degrees about x then y ends somewhere different from y then x."""
    canvas = Canvas(860, 330)
    mesh = g3.box(56, 56, 56)

    def colors(tag: int, lit: float) -> RGB:
        base = AMBER if tag == 0 else CYAN
        return mix(BACKGROUND, base, 0.25 + 0.75 * lit)

    quarter = math.radians(90)
    rows = (
        ("x, then y", [Rotation(), Rotation.about_x(-quarter), Rotation.about_y(quarter) * Rotation.about_x(-quarter)]),
        ("y, then x", [Rotation(), Rotation.about_y(quarter), Rotation.about_x(-quarter) * Rotation.about_y(quarter)]),
    )
    for row, (label, poses) in enumerate(rows):
        y = 100 + row * 150
        canvas.text((60, y), label, TEXT, 15)
        turns = [f"{'-90' if axis == 'x' else '90'}° about {axis}" for axis in label.split(", then ")]
        for step, pose in enumerate(poses):
            x = 230 + step * 230
            solid(canvas, View((x, y), 0.95, yaw=-30, pitch=20), mesh, pose, colors=colors)
            if step < 2:
                canvas.arrow((x + 70, y), (x + 150, y), MUTED, 2)
                canvas.text((x + 110, y - 16), turns[step], MUTED, 12)
    canvas.text(
        (430, 22), "The front face is amber. Same two quarter turns, different order, different result.", MUTED, 13
    )
    return [canvas.finish()]


def projection() -> list[Image.Image]:
    """Side view of perspective and orthographic projection, with an object moving nearer and farther."""
    frames = []
    count = 100
    for index in range(count):
        t = ease(abs(1 - 2 * index / count))
        # Wide enough for the orthographic caption at the right edge.
        canvas = Canvas(900, 380)
        for panel, (title, perspective) in enumerate((("Perspective", True), ("Orthographic (perspective=0)", False))):
            left = 30 + panel * 430
            screen_x = left + 250
            eye = (left + 390, 200)
            ground = 200
            canvas.text((left + 200, 28), title, TEXT, 15)
            canvas.line((screen_x, 70), (screen_x, 330), MUTED, 2)
            canvas.text((screen_x, 350), "screen (z = 0)", MUTED, 12)
            if perspective:
                canvas.circle(eye, 7, AMBER)
                canvas.text((eye[0], eye[1] + 24), "camera", AMBER, 12)
            else:
                canvas.text((left + 340, ground + 110), "camera infinitely far", AMBER, 12)
                canvas.text((left + 340, ground + 126), "away: rays are parallel", AMBER, 12)
            # An object moving between near and far, standing on the axis.
            depth_x = left + 30 + 170 * t
            height = 70
            top, bottom = (depth_x, ground - height), (depth_x, ground + height)
            canvas.line(top, bottom, CYAN, 6)
            for end in (top, bottom):
                if perspective:
                    canvas.line(end, eye, mix(CYAN, BACKGROUND, 0.5), 1.5, dash=5)
                    k = (screen_x - end[0]) / (eye[0] - end[0])
                    hit = (screen_x, end[1] + (eye[1] - end[1]) * k)
                else:
                    canvas.line(end, (eye[0], end[1]), mix(CYAN, BACKGROUND, 0.5), 1.5, dash=5)
                    hit = (screen_x, end[1])
                canvas.circle(hit, 4, WHITE)
            if perspective:
                k = (screen_x - depth_x) / (eye[0] - depth_x)
                image = (ground - height + height * k, ground + height - height * k)
            else:
                image = (ground - height, ground + height)
            canvas.line((screen_x + 10, image[0]), (screen_x + 10, image[1]), WHITE, 5)
            canvas.text((screen_x + 22, ground), "drawn size", WHITE, 12, "lm")
        canvas.text(
            (430, 368), "With perspective, an object's drawn size shrinks with its distance from the camera.", MUTED, 13
        )
        frames.append(canvas.finish())
    return frames


def perspective_strength() -> list[Image.Image]:
    """Show the same near and far objects seen with no perspective, the default, and a close camera."""
    canvas = Canvas(860, 300)
    settings = (
        ("perspective=0", None, "no shrinking"),
        ("perspective=1", 240.0, "camera 120 away"),
        ("perspective=2", 120.0, "camera 60 away"),
    )
    for panel, (label, distance, note) in enumerate(settings):
        left = 20 + panel * 285
        screen_x = left + 170
        ground = 150
        canvas.text((left + 140, 26), label, TEXT, 14, mono=True)
        canvas.text((left + 140, 46), note, MUTED, 12)
        canvas.text((left + 75, 80), "objects", MUTED, 11)
        canvas.text((screen_x + 30, 80), "screen", MUTED, 11)
        canvas.line((screen_x, 90), (screen_x, 230), MUTED, 2)
        for x, color, offset in ((screen_x - 20, CYAN, 8), (screen_x - 120, PURPLE, 16)):
            canvas.line((x, ground - 40), (x, ground + 40), color, 5)
            k = 1.0
            if distance is not None:
                eye = (screen_x + distance / 2, ground)
                k = (eye[0] - screen_x) / (eye[0] - x)
                if color == PURPLE:
                    for end_y in (ground - 40, ground + 40):
                        canvas.line((x, end_y), eye, mix(PURPLE, BACKGROUND, 0.4), 1, dash=4)
                    canvas.circle(eye, 5, AMBER)
            canvas.line((screen_x + offset, ground - 40 * k), (screen_x + offset, ground + 40 * k), color, 4)
        canvas.text((left + 140, 262), "near (cyan) and far (purple) objects", MUTED, 11)
    return [canvas.finish()]


def depth_buffer() -> list[Image.Image]:
    """Side view: one ray per cell from the camera; each cell keeps the nearest surface its ray meets."""
    canvas = Canvas(860, 380)
    eye = (780, 190)
    screen_x = 600
    canvas.circle(eye, 7, AMBER)
    canvas.text((eye[0], eye[1] + 24), "camera", AMBER, 12)
    canvas.text((screen_x, 70), "cells", TEXT, 14)
    near = (320, 110, 420, 210)  # left, top, right, bottom
    far = (140, 150, 300, 310)
    canvas.rect(far[0], far[1], far[2], far[3], mix(PURPLE, BACKGROUND, 0.3), PURPLE)
    canvas.rect(near[0], near[1], near[2], near[3], mix(CYAN, BACKGROUND, 0.55), CYAN)
    canvas.text(((far[0] + far[2]) / 2, far[3] + 18), "farther surface", PURPLE, 12)
    canvas.text(((near[0] + near[2]) / 2, near[1] - 14), "nearer surface", CYAN, 12)
    size = 12
    for cell in range(-6, 8):
        cell_y = eye[1] + cell * size
        direction = (screen_x - eye[0], cell_y - eye[1])
        end, color = (80.0, eye[1] + direction[1] * (80 - eye[0]) / direction[0]), FAINT
        for box, box_color in ((near, CYAN), (far, PURPLE)):
            s = (box[2] - eye[0]) / direction[0]
            y = eye[1] + direction[1] * s
            if box[1] <= y <= box[3]:
                end, color = (box[2], y), box_color
                break  # The near box is checked first, and its face is nearer the camera.
        canvas.line(eye, end, mix(color, BACKGROUND, 0.4), 1.2)
        canvas.rect(screen_x - size / 2, cell_y - size / 2, screen_x + size / 2, cell_y + size / 2, color, BACKGROUND)
    canvas.text(
        (430, 362),
        "Each cell keeps only the nearest surface its ray meets, so nearer shapes hide farther ones.",
        MUTED,
        13,
    )
    return [canvas.finish()]


def back_faces() -> list[Image.Image]:
    """Seen from above: faces whose normals point toward the camera are drawn; the rest are skipped."""
    frames = []
    count = 100
    for index in range(count):
        angle = 2 * math.pi * index / count
        canvas = Canvas(760, 360)
        eye = (380, 330)
        canvas.circle(eye, 7, AMBER)
        canvas.text((eye[0] + 40, eye[1]), "camera", AMBER, 12)
        center = (380, 160)
        corners = []
        for k in range(6):
            a = angle + 2 * math.pi * k / 6
            corners.append((center[0] + 85 * math.cos(a), center[1] + 85 * math.sin(a)))
        for k in range(6):
            a, b = corners[k], corners[(k + 1) % 6]
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            normal = (mid[0] - center[0], mid[1] - center[1])
            length = math.hypot(*normal)
            normal = (normal[0] / length, normal[1] / length)
            toward = (eye[0] - mid[0], eye[1] - mid[1])
            facing = normal[0] * toward[0] + normal[1] * toward[1] > 0
            canvas.line(a, b, CYAN if facing else FAINT, 4 if facing else 2, dash=0 if facing else 5)
            tip = (mid[0] + normal[0] * 40, mid[1] + normal[1] * 40)
            canvas.arrow(mid, tip, WHITE if facing else FAINT, 1.5, 8)
        canvas.text((380, 26), "A prism seen from above. Arrows are face normals.", TEXT, 14)
        canvas.text((150, 300), "drawn: normal points toward the camera", CYAN, 12)
        canvas.text((150, 320), "skipped: normal points away", MUTED, 12)
        frames.append(canvas.finish())
    return frames


def mesh_anatomy() -> list[Image.Image]:
    """Show a cube's vertices, one face's corner order and normal, and a star cap split into triangles."""
    canvas = Canvas(860, 380)
    view = View((230, 200), 2.2, yaw=-35, pitch=22)
    mesh = g3.box(60, 60, 60)
    for a, b in mesh.edges():
        canvas.line(view(mesh.vertices[a]), view(mesh.vertices[b]), MUTED, 1.5)
    face = mesh.faces[1]  # The right face, +x.
    canvas.polygon([view(mesh.vertices[i]) for i in face.indices], mix(CYAN, BACKGROUND, 0.7), CYAN, 2.5)
    for order, vertex in enumerate(face.indices):
        p = view(mesh.vertices[vertex])
        canvas.circle(p, 11, BACKGROUND, CYAN, 2)
        canvas.text(p, str(order), CYAN, 12)
    # The corner order, as a turning arrow on the face.
    ring = [view(Vec3(30, 14 * math.sin(a), 14 * math.cos(a))) for a in [k * math.pi / 12 for k in range(4, 26)]]
    for a, b in zip(ring, ring[1:-1]):
        canvas.line(a, b, WHITE, 2)
    canvas.arrow(ring[-2], ring[-1], WHITE, 2, 9)
    canvas.arrow(view(Vec3(30, 0, 0)), view(Vec3(85, 0, 0)), AMBER, 3, 12)
    canvas.text((view(Vec3(92, 0, 0))[0] + 6, view(Vec3(92, 0, 0))[1]), "normal", AMBER, 13, "lm")
    canvas.text((230, 26), "A face lists its corners counterclockwise", TEXT, 14)
    canvas.text((230, 44), "as seen from outside, so its normal points out", TEXT, 14)
    # A star cap and its fan of triangles.
    cx, cy = 650, 200
    points = []
    for k in range(10):
        radius = 120 if k % 2 == 0 else 52
        a = -math.pi / 2 + 2 * math.pi * k / 10
        points.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
    for k in range(10):
        color = mix(PURPLE, CYAN, k / 9)
        canvas.polygon([(cx, cy), points[k], points[(k + 1) % 10]], mix(color, BACKGROUND, 0.35), color, 1.5)
    canvas.circle((cx, cy), 4, WHITE)
    canvas.text((cx, 26), "A star isn't convex, so its cap", TEXT, 14)
    canvas.text((cx, 44), "is a fan of triangles around the center", TEXT, 14)
    return [canvas.finish()]


def lambert() -> list[Image.Image]:
    """Show a face turning under a fixed light: the angle between normal and light picks the symbol and color."""
    frames = []
    count = 120
    ramp = ".,-~:;=!*#$@"
    light_angle = math.radians(60)
    for index in range(count):
        angle = math.radians(-80) + math.radians(160) * ease(abs(1 - 2 * index / count))
        canvas = Canvas(860, 360)
        center = (240, 220)
        nx, ny = math.cos(angle + math.pi / 2), math.sin(angle + math.pi / 2)
        half = 110
        # The normal is drawn as (nx, -ny) on screen, where y points down, so the face runs along (ny, nx).
        a = (center[0] - half * ny, center[1] - half * nx)
        b = (center[0] + half * ny, center[1] + half * nx)
        brightness = max(0.0, math.cos(angle + math.pi / 2 - light_angle))
        canvas.line((a[0], a[1]), (b[0], b[1]), shade(brightness), 8)
        normal_tip = (center[0] + 100 * nx, center[1] - 100 * ny)
        canvas.arrow(center, normal_tip, WHITE, 2.5, 11)
        canvas.text((normal_tip[0], normal_tip[1] - 16), "normal", WHITE, 12)
        light_tip = (center[0] + 140 * math.cos(light_angle), center[1] - 140 * math.sin(light_angle))
        canvas.arrow(center, light_tip, AMBER, 2.5, 11)
        canvas.circle(light_tip, 9, AMBER)
        canvas.text((light_tip[0] + 18, light_tip[1]), "light", AMBER, 12, "lm")
        # The angle between them.
        start = -math.degrees(max(angle + math.pi / 2, light_angle))
        end = -math.degrees(min(angle + math.pi / 2, light_angle))
        canvas.arc(center, 40, start, end, MUTED, 2)
        canvas.text((240, 26), "lambert = max(0, cos(angle between normal and light))", TEXT, 14)
        # The brightness bar and the symbol it picks.
        canvas.text((560, 100), f"lambert = {brightness:.2f}", TEXT, 14, "lm", mono=True)
        canvas.rect(560, 130, 820, 150, None, FAINT)
        canvas.rect(560, 130, 560 + 260 * brightness, 150, shade(brightness))
        chosen = min(len(ramp) - 1, int(brightness * len(ramp)))
        for k, symbol in enumerate(ramp):
            x = 572 + k * 21.5
            color = shade((k + 0.5) / len(ramp))
            if k == chosen:
                canvas.rect(x - 10, 172, x + 10, 204, (40, 42, 50), WHITE)
            canvas.text((x, 188), symbol, color, 18, mono=True)
        canvas.text((690, 232), "Shaded() symbols and colors, unlit to fully lit", MUTED, 12)
        canvas.text((690, 300), "Faces turned from the light still get the", MUTED, 12)
        canvas.text((690, 318), "first symbol, so they never vanish.", MUTED, 12)
        frames.append(canvas.finish())
    return frames


def uv_mapping() -> list[Image.Image]:
    """Show a face's texture coordinates, the text laid over it, and how a cylinder wraps text around its side."""
    canvas = Canvas(860, 360)
    text = ["TerminalTextEffects ", "TerminalTextEffects "]
    # One face with u and v.
    left, top, width, height = 60, 80, 260, 160
    canvas.rect(left, top, left + width, top + height, (30, 32, 38), CYAN)
    canvas.text((left + width / 2, 40), "One face: u across, v up, each 0 to 1", TEXT, 14)
    for row in range(5):
        line = text[row % 2]
        for column in range(24):
            x = left + 10 + column * 10.4
            y = top + 18 + row * 30
            canvas.text((x, y), line[column % len(line)], mix(CYAN, WHITE, 0.4), 16, mono=True)
    canvas.arrow((left, top + height + 20), (left + width, top + height + 20), RED, 2)
    canvas.text((left + width + 14, top + height + 20), "u", RED, 14, "lm")
    canvas.arrow((left - 20, top + height), (left - 20, top), GREEN, 2)
    canvas.text((left - 20, top - 14), "v", GREEN, 14)
    canvas.text((left, top + height + 44), "(0, 0)", MUTED, 11)
    canvas.text((left + width, top - 14), "(1, 1)", MUTED, 11)
    canvas.text((190, 330), "Row 0 of the text is at the top of the face.", MUTED, 12)
    # A cylinder, seen from above, with the text wrapped around it.
    cx, cy, radius = 640, 175, 95
    canvas.text((cx, 40), "A cylinder wraps the text around its side", TEXT, 14)
    message = "TERMINAL TEXT EFFECTS · "
    count = 48
    for k in range(count):
        a = math.pi / 2 - 2 * math.pi * k / count
        x, y = cx + radius * math.cos(a), cy + radius * math.sin(a)
        facing = math.sin(a) > 0
        canvas.text((x, y), message[k % len(message)], AMBER if facing else FAINT, 15, mono=True)
    canvas.circle((cx, cy), radius - 18, None, FAINT, 1)
    canvas.circle((cx, cy + radius + 30), 6, AMBER)
    canvas.text((cx + 14, cy + radius + 30), "viewer", AMBER, 12, "lm")
    canvas.text((cx, 330), "Seen from above. The text starts at the front and repeats around.", MUTED, 12)
    return [canvas.finish()]


def tween_timeline() -> list[Image.Image]:
    """Tweens queue one after another; together=True runs one alongside the tween before it."""
    canvas = Canvas(860, 300)
    left, unit = 150, 2.4
    canvas.text((430, 26), "One body's queue, frame by frame", TEXT, 15)
    rows = [
        ("hold(30)", 0, 30, FAINT, 0),
        ('spin("y", frames=120)', 30, 120, CYAN, 0),
        ('spin("x", ..., together=True)', 30, 120, PURPLE, 1),
        ('settle("y", frames=90)', 150, 90, AMBER, 0),
    ]
    for label, start, length, color, lane in rows:
        y = 80 + lane * 44 + (88 if label.startswith("settle") else 0)
        canvas.rect(left + start * unit, y, left + (start + length) * unit, y + 30, mix(color, BACKGROUND, 0.45), color)
        canvas.text((left + start * unit + 8, y + 15), label, TEXT, 12, "lm", mono=True)
    canvas.line((left, 240), (left + 260 * unit, 240), MUTED, 1.5)
    for frame in range(0, 261, 30):
        x = left + frame * unit
        canvas.line((x, 236), (x, 244), MUTED, 1.5)
        canvas.text((x, 258), str(frame), MUTED, 11)
    canvas.text((left - 12, 258), "frame", MUTED, 11, "rm")
    end = left + 240 * unit
    canvas.line((end, 70), (end, 236), WHITE, 1.5, dash=4)
    canvas.text((end + 8, 74), "on_complete", WHITE, 12, "lm", mono=True)
    canvas.text((430, 285), "space.step() plays one frame of the tweens at the front of each body's queue.", MUTED, 12)
    return [canvas.finish()]


def near_plane() -> list[Image.Image]:
    """Side view: a box slides toward the camera, and the part nearer than the near plane is clipped away."""
    frames = []
    count = 120
    eye = (790, 180)
    near_x = 730
    half = 50
    for index in range(count):
        t = ease(abs(1 - 2 * index / count))
        canvas = Canvas(860, 360)
        canvas.text((430, 26), "Anything nearer than camera.near is clipped away", TEXT, 14)
        for spread in (-150, 150):
            canvas.line(eye, (60, eye[1] + spread), FAINT, 1, dash=4)
        canvas.line((near_x, 70), (near_x, 290), MUTED, 2, dash=5)
        canvas.text((near_x, 58), "near plane", MUTED, 12)
        # The box, from far away to just past the camera.
        center_x = 760 - 620 * t
        left, right = center_x - half, center_x + half
        top, bottom = eye[1] - half, eye[1] + half
        if right > near_x:
            cut = max(left, near_x)
            for a, b in (((cut, top), (right, top)), ((right, top), (right, bottom)), ((right, bottom), (cut, bottom))):
                canvas.line(a, b, MUTED, 1.5, dash=4)
            if right - cut > 24:
                canvas.text(((cut + right) / 2, top - 14), "clipped", MUTED, 12)
        if left < near_x:
            canvas.rect(left, top, min(right, near_x), bottom, mix(CYAN, BACKGROUND, 0.55))
            canvas.polygon(
                [(left, top), (min(right, near_x), top), (min(right, near_x), bottom), (left, bottom)], None, CYAN, 2
            )
            if min(right, near_x) - left > 40:
                canvas.text(((left + min(right, near_x)) / 2, bottom + 16), "drawn", CYAN, 12)
        canvas.circle(eye, 7, AMBER)
        canvas.text((eye[0], 262), "camera", AMBER, 12)
        canvas.line((near_x, 300), (eye[0], 300), WHITE, 1.5)
        for x in (near_x, eye[0]):
            canvas.line((x, 294), (x, 306), WHITE, 1.5)
        canvas.text(((near_x + eye[0]) / 2, 318), "camera.near", WHITE, 12, mono=True)
        canvas.text(
            (400, 318), "Points closer than near aren't projected; faces are cut where they cross it.", MUTED, 12
        )
        frames.append(canvas.finish())
    return frames


def cell_snapping() -> list[Image.Image]:
    """Show a point moving smoothly across tall cells while the character drawn for it jumps from cell to cell."""
    frames = []
    count = 150
    cell_w, cell_h = 22, 44
    columns, rows = 30, 5
    origin = (60, 60)

    def path(t: float) -> tuple[float, float]:
        return (0.6 + 28.8 * t, 2.5 - 1.7 * math.sin(2 * math.pi * t))

    def to_px(x: float, y: float) -> Point:
        return (origin[0] + x * cell_w, origin[1] + y * cell_h)

    curve = [to_px(*path(k / 120)) for k in range(121)]
    for index in range(count):
        t = index / count
        canvas = Canvas(780, 360)
        canvas.text(
            (390, 26),
            "A projected point is drawn in the cell it falls in, so motion moves in whole-cell steps",
            TEXT,
            14,
        )
        # Cells the point has already passed through.
        visited = {tuple(int(v) for v in path(k / 300)) for k in range(int(t * 300) + 1)}
        for column, row in visited:
            x0, y0 = to_px(column, row)
            canvas.rect(x0, y0, x0 + cell_w, y0 + cell_h, mix(PURPLE, BACKGROUND, 0.55))
        x, y = path(t)
        column, row = int(x), int(y)
        x0, y0 = to_px(column, row)
        canvas.rect(x0, y0, x0 + cell_w, y0 + cell_h, CYAN)
        for k in range(columns + 1):
            canvas.line(to_px(k, 0), to_px(k, rows), FAINT, 1)
        for k in range(rows + 1):
            canvas.line(to_px(0, k), to_px(columns, k), FAINT, 1)
        center = to_px(column + 0.5, row + 0.5)
        canvas.text(center, "@", BACKGROUND, 22, mono=True)
        for a, b in zip(curve, curve[1:]):
            canvas.line(a, b, mix(AMBER, BACKGROUND, 0.6), 1.2)
        dot = to_px(x, y)
        canvas.line(dot, center, WHITE, 1.2)
        canvas.circle(dot, 5, AMBER)
        # Legend.
        canvas.circle((150, 310), 5, AMBER)
        canvas.text((164, 310), "the exact projected point: moves smoothly", MUTED, 12, "lm")
        canvas.rect(450, 300, 460, 320, CYAN)
        canvas.text((470, 310), "the cell it's drawn in: jumps", MUTED, 12, "lm")
        canvas.text((390, 336), "Earlier cells (purple) form a staircase, not the smooth curve.", MUTED, 12)
        frames.append(canvas.finish())
    return frames


def winding() -> list[Image.Image]:
    """Show the same triangle with its corners listed counterclockwise, facing the camera, and clockwise, culled."""
    canvas = Canvas(820, 360)
    canvas.text((410, 26), "Corner order decides which way a face points", TEXT, 14)
    canvas.text((410, 44), "Both triangles as seen from the camera", MUTED, 12)
    radius = 100
    panels = (
        (210, (-90, 150, 30), True),
        (610, (-90, 30, 150), False),
    )
    for cx, angles, facing in panels:
        cy = 190
        corners = [(cx + radius * math.cos(math.radians(a)), cy + radius * math.sin(math.radians(a))) for a in angles]
        color = CYAN if facing else MUTED
        if facing:
            canvas.polygon(corners, mix(CYAN, BACKGROUND, 0.6), CYAN, 2.5)
        else:
            for a, b in zip(corners, corners[1:] + corners[:1]):
                canvas.line(a, b, MUTED, 2, dash=5)
        # The order the corners are listed in, as a turning arrow.
        sweep = -1 if facing else 1
        angles_on_ring = [math.radians(-90 + sweep * k * 12) for k in range(-12, 13)]
        ring = [(cx + 34 * math.cos(a), cy + 34 * math.sin(a)) for a in angles_on_ring]
        for a, b in zip(ring, ring[1:-1]):
            canvas.line(a, b, WHITE if facing else MUTED, 2)
        canvas.arrow(ring[-2], ring[-1], WHITE if facing else MUTED, 2, 9)
        # The normal: a dot means toward the viewer, a cross means away.
        normal = (cx, cy)
        canvas.circle(normal, 10, BACKGROUND, AMBER if facing else MUTED, 2)
        if facing:
            canvas.circle(normal, 3.5, AMBER)
        else:
            for dx in (-1, 1):
                canvas.line((normal[0] - 5, normal[1] - 5 * dx), (normal[0] + 5, normal[1] + 5 * dx), MUTED, 2)
        for order, corner in enumerate(corners):
            canvas.circle(corner, 11, BACKGROUND, color, 2)
            canvas.text(corner, str(order), color, 12)
        if facing:
            canvas.text((cx, 318), "counterclockwise: faces the camera, drawn", CYAN, 12)
            canvas.text((cx, 336), "normal points out of the screen, toward you", MUTED, 12)
        else:
            canvas.text((cx, 318), "clockwise: faces away, culled", MUTED, 12)
            canvas.text((cx, 336), "normal points into the screen, away from you", MUTED, 12)
    return [canvas.finish()]


def texture_seam() -> list[Image.Image]:
    """Show text unrolled as a strip and wrapped once around a turning cylinder, where its two ends meet at the seam."""
    frames = []
    count = 120
    message = "TERMINAL TEXT EFFECTS "
    columns = len(message)
    cell_w, cell_h = 15, 26
    strip_left, strip_top = 50, 130
    cx, cy, radius, tall, tilt = 640, 190, 95, 150, 0.24
    rows = (-44.0, 0.0, 44.0)

    def around(theta: float, y: float) -> Point:
        return (cx + radius * math.sin(theta), cy - y + radius * tilt * math.cos(theta))

    for index in range(count):
        turn = -2 * math.pi * index / count
        canvas = Canvas(860, 360)
        canvas.text((430, 26), "Text wraps all the way around, meeting itself at the seam", TEXT, 14)
        # The strip, u from 0 to 1. Columns facing the viewer on the cylinder are brighter.
        canvas.text((strip_left + columns * cell_w / 2, 92), "The text unrolled: u runs 0 to 1", MUTED, 12)
        for column, char in enumerate(message):
            facing = math.cos(2 * math.pi * (column + 0.5) / columns + turn)
            x0 = strip_left + column * cell_w
            canvas.rect(x0, strip_top, x0 + cell_w, strip_top + 3 * cell_h, (30, 32, 38) if facing > 0 else None, FAINT)
            for row in range(3):
                color = mix(FAINT, CYAN, 0.3 + 0.7 * facing) if facing > 0 else FAINT
                canvas.text((x0 + cell_w / 2, strip_top + (row + 0.5) * cell_h), char, color, 16, mono=True)
        strip_right = strip_left + columns * cell_w
        for x, label in ((strip_left, "u = 0"), (strip_right, "u = 1")):
            canvas.line((x, strip_top - 10), (x, strip_top + 3 * cell_h + 10), AMBER, 3)
            canvas.text((x, strip_top + 3 * cell_h + 26), label, AMBER, 12)
        canvas.text((strip_left + columns * cell_w / 2, 292), "Brighter columns face you on the cylinder.", MUTED, 12)
        # The cylinder body and outline.
        body = [around(math.pi / 2 + math.pi * k / 32, tall / 2) for k in range(33)]
        body += [around(-math.pi / 2 + math.pi * k / 32, -tall / 2) for k in range(33)]
        canvas.polygon(body, (30, 32, 38))
        top_ring = [around(2 * math.pi * k / 64, tall / 2) for k in range(65)]
        bottom_front = [around(-math.pi / 2 + math.pi * k / 32, -tall / 2) for k in range(33)]
        for ring in (top_ring, bottom_front):
            for a, b in zip(ring, ring[1:]):
                canvas.line(a, b, MUTED, 1.5)
        canvas.line(around(math.pi / 2, tall / 2), around(math.pi / 2, -tall / 2), MUTED, 1.5)
        canvas.line(around(-math.pi / 2, tall / 2), around(-math.pi / 2, -tall / 2), MUTED, 1.5)
        # The text on the front half.
        for column, char in enumerate(message):
            theta = 2 * math.pi * (column + 0.5) / columns + turn
            facing = math.cos(theta)
            if facing < 0.3:
                continue
            for y in rows:
                canvas.text(around(theta, y), char, mix(FAINT, CYAN, facing), 18, mono=True)
        # The seam, where u = 1 meets u = 0.
        seam = turn
        if math.cos(seam) > 0:
            canvas.line(around(seam, tall / 2), around(seam, -tall / 2), AMBER, 3)
            if math.cos(seam) > 0.3:
                top = around(seam, tall / 2)
                canvas.text((top[0], cy - tall / 2 - radius * tilt - 18), "seam: u = 1 meets u = 0", AMBER, 12)
        else:
            # Behind the cylinder: only its end on the far rim of the top shows.
            canvas.circle(around(seam, tall / 2), 3.5, mix(AMBER, BACKGROUND, 0.3))
        canvas.text((cx, 336), "The last column sits right beside the first.", MUTED, 12)
        frames.append(canvas.finish())
    return frames


def camera_movement() -> list[Image.Image]:
    """Show camera-local travel and an orbit around a stationary cube from above."""
    frames = []
    for frame in range(90):
        canvas = Canvas(660, 380)
        canvas.text((330, 25), "Move the viewpoint, keep the scene still", TEXT, 18)
        center = (330.0, 195.0)
        radius = 115
        angle = 2 * math.pi * frame / 90
        eye = (center[0] + radius * math.sin(angle), center[1] + radius * math.cos(angle))
        canvas.circle(center, radius, None, FAINT, 1)
        canvas.rect(306, 171, 354, 219, PURPLE, CYAN)
        canvas.text(center, "cube", WHITE, 12)
        canvas.line(eye, center, MUTED, 1, dash=5)
        forward = (-math.sin(angle), -math.cos(angle))
        right = (math.cos(angle), -math.sin(angle))
        canvas.arrow(eye, (eye[0] + forward[0] * 50, eye[1] + forward[1] * 50), GREEN)
        canvas.arrow(eye, (eye[0] + right[0] * 45, eye[1] + right[1] * 45), AMBER)
        canvas.circle(eye, 7, CYAN)
        canvas.text((75, 125), "camera", CYAN, 14, anchor="lm")
        canvas.text((75, 155), "orbit", MUTED, 14, anchor="lm")
        canvas.text((505, 165), "dolly: forward", GREEN, 14, anchor="lm")
        canvas.text((505, 195), "truck: right", AMBER, 14, anchor="lm")
        canvas.text((330, 350), "Top view: the camera keeps looking at the cube.", MUTED, 14)
        frames.append(canvas.finish())
    return frames


CLIPPED: set[str] = set()
"""Labels and markers drawn reaching past a frame's edges since this was last cleared, so tests can catch them."""


def find_clipped(name: str) -> set[str]:
    """Render the diagram `name` and return the labels and markers in any frame that reach past its edges."""
    CLIPPED.clear()
    DIAGRAMS[name]()
    return set(CLIPPED)


DIAGRAMS: dict[str, Callable[[], list[Image.Image]]] = {
    "cell_sampling": cell_sampling,
    "world_axes": world_axes,
    "tall_cells": tall_cells,
    "transform_order": transform_order,
    "transform_pipeline": transform_pipeline,
    "rotation_axes": rotation_axes,
    "rotation_local": rotation_local,
    "rotation_order": rotation_order,
    "projection": projection,
    "camera_movement": camera_movement,
    "perspective_strength": perspective_strength,
    "depth_buffer": depth_buffer,
    "back_faces": back_faces,
    "mesh_anatomy": mesh_anatomy,
    "lambert": lambert,
    "uv_mapping": uv_mapping,
    "tween_timeline": tween_timeline,
    "near_plane": near_plane,
    "cell_snapping": cell_snapping,
    "winding": winding,
    "texture_seam": texture_seam,
}


def main(argv: Sequence[str] | None = None) -> int:
    """Render the named diagrams, or all of them, and return the exit status."""
    parser = argparse.ArgumentParser(description="Render the 3D Effects concept diagrams.")
    parser.add_argument("names", nargs="*", help="diagrams to render (default: all)")
    parser.add_argument("--list", action="store_true", help="list diagram names and exit")
    parser.add_argument("--out", type=Path, default=OUT_DIR, help=f"output directory (default: {OUT_DIR})")
    args = parser.parse_args(argv)
    if args.list:
        print("\n".join(DIAGRAMS))
        return 0
    unknown = [name for name in args.names if name not in DIAGRAMS]
    if unknown:
        parser.error(f"unknown diagrams: {', '.join(unknown)}")
    for name in args.names or DIAGRAMS:
        path = save(name, DIAGRAMS[name](), args.out)
        print(f"{name}: {path.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
