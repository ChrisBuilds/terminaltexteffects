"""Drawing bodies: looks for their faces, and painting them in one depth order with the characters.

    cube = world.body(Cube(16))
    cube.draw(Shaded())                      # or Solid(), Textured(), Wireframe()
    cube.draw(faces={"front": Textured(), "top": Solid("#")})

A drawn body is shown with characters the world creates and manages, one per covered cell, so an effect's own
characters are never used for it. Drawn cells and characters are painted in one order: by layer, then farther
first, so the nearest wins each cell. A character sitting on its body's surface (height 0) and facing the camera
draws over that body's own cell beneath it, like a decal, and anything genuinely in front of it still hides it.

Classes:
    Shaded, Solid, Textured, Wireframe: Looks for drawing a body.
"""

from __future__ import annotations

import math
import typing
import weakref
from dataclasses import dataclass

from terminaltexteffects.utils import geometry3d as g3
from terminaltexteffects.utils.exceptions import InvalidSymbolError
from terminaltexteffects.utils.graphics import Color, ColorPair, Gradient
from terminaltexteffects.utils.terminal_text import get_symbol_cell_width

if typing.TYPE_CHECKING:
    from terminaltexteffects.engine.base_character import EffectCharacter
    from terminaltexteffects.engine.terminal import Terminal
    from terminaltexteffects.engine.world import Body, World
    from terminaltexteffects.utils.geometry import Coord

__all__ = ["Look", "Shaded", "Solid", "Textured", "Wireframe"]

_BRAND_STOPS = ("#8A008A", "#00D1FF", "#ffffff")
_DIM = Color("#7a3a86")
_SHADE_SYMBOLS = ".,-~:;=!*#$@"
_AMBIENT = 0.15
_TEXT_NUDGE = 1e-6
_SURFACE_BIAS = 1e-6
"""How much farther a drawn cell is ordered than it is, so a character exactly on the surface draws on top."""
_DECAL_REACH = 2.0
"""How far behind its body's drawn cell, in units, a character on the surface still draws over it. It covers
the gap between a curved surface and the flat facets it is drawn with, and the cell-center sampling at folds."""


@dataclass(frozen=True)
class Shaded:
    """Fill faces with a symbol and color picked by how directly each face meets the light.

    Attributes:
        gradient (Gradient | None): Colors from unlit to fully lit. `None` uses the TTE brand colors.
        symbols (str): Symbols from unlit to fully lit.

    Raises:
        ValueError: If `symbols` is empty or contains a symbol that is not one printable cell wide.

    """

    gradient: Gradient | None = None
    symbols: str = _SHADE_SYMBOLS

    def __post_init__(self) -> None:
        """Validate the symbols."""
        if not self.symbols:
            msg = "Shaded needs at least one symbol."
            raise ValueError(msg)
        for symbol in self.symbols:
            _check_one_cell(symbol)


@dataclass(frozen=True)
class Solid:
    """Fill faces with one symbol, colored by the light.

    Attributes:
        symbol (str): The fill symbol, one cell wide.
        gradient (Gradient | None): Colors from unlit to fully lit. `None` uses the TTE brand colors.

    Raises:
        ValueError: If `symbol` is not one printable character one cell wide.

    """

    symbol: str = "█"
    gradient: Gradient | None = None

    def __post_init__(self) -> None:
        """Validate the symbol."""
        _check_one_cell(self.symbol)


@dataclass(frozen=True)
class Textured:
    """Wrap text over the faces, colored by the light. Text repeats by default or clamps with `repeat=False`.

    Each cell shows one symbol, so wide characters (such as CJK) are left blank.

    Faces without a texture layout (prism and cylinder caps, polyhedra, the torus) are shaded in `back_color`.

    Attributes:
        text (str | None): The text to wrap. `None` uses the effect's input text.
        gradient (Gradient | None): Colors from unlit to fully lit. `None` uses the TTE brand colors.
        back (str): `"hide"` draws spaces in the text as blank surface. `"dim"` lets the far side show through
            them, drawn in `back_color`.
        back_color (Color): Color of the far side and of faces without a texture layout.
        offset (tuple[float, float]): `(column_offset, row_offset)` in text cells, added before sampling. Positive
            values scroll left/up.
        repeat (bool): Repeat the text, or clamp sampling to its edge cells when false.
        scale (float): Positive text size multiplier in both dimensions; 2 doubles each character's footprint.

    Raises:
        ValueError: If `back` is not `"hide"` or `"dim"`, `scale` is not finite and positive,
            or `offset` does not contain two finite coordinates.

    """

    text: str | None = None
    gradient: Gradient | None = None
    back: typing.Literal["hide", "dim"] = "hide"
    back_color: Color = _DIM
    offset: tuple[float, float] = (0.0, 0.0)
    repeat: bool = True
    scale: float = 1.0

    def __post_init__(self) -> None:
        """Validate texture sampling settings."""
        if self.back not in ("hide", "dim"):
            msg = 'back must be "hide" or "dim".'
            raise ValueError(msg)
        if not math.isfinite(self.scale) or self.scale <= 0:
            msg = "Texture scale must be finite and positive."
            raise ValueError(msg)
        if len(self.offset) != 2 or not all(math.isfinite(value) for value in self.offset):
            msg = "Texture offset must contain two finite coordinates."
            raise ValueError(msg)


@dataclass(frozen=True)
class Wireframe:
    """Draw only the edges, with symbols that follow each edge's slope.

    Attributes:
        color (Color): Color of edges on faces turned toward the viewer.
        hidden_color (Color | None): Color of hidden edges, or `None` to leave them out.
        depth_test (bool): Test edges against the mesh's filled depth buffer. Use for concave meshes; the default
            only tests adjacent face orientation.

    """

    color: Color = Color("#00D1FF")
    hidden_color: Color | None = _DIM
    depth_test: bool = False


Look = typing.Union[Shaded, Solid, Textured, Wireframe]
"""How a body is drawn: `Shaded`, `Solid`, `Textured` or `Wireframe`."""

_default_gradient: Gradient | None = None


def _gradient(gradient: Gradient | None) -> Gradient:
    """Return `gradient`, or the shared brand gradient."""
    global _default_gradient  # noqa: PLW0603
    if gradient is not None:
        return gradient
    if _default_gradient is None:
        _default_gradient = Gradient(*(Color(stop) for stop in _BRAND_STOPS), steps=12)
    return _default_gradient


def _check_one_cell(symbol: str) -> None:
    """Raise `ValueError` unless `symbol` is one printable symbol one cell wide, as each surface cell needs."""
    try:
        width = get_symbol_cell_width(symbol)
    except InvalidSymbolError:
        width = 0
    if width != 1:
        msg = f"Surface symbols must be one printable character one cell wide, not {symbol!r}."
        raise ValueError(msg)


def _text_grid(text: str) -> tuple[list[str], int]:
    """Split `text` into lines of one-cell symbols and return them with the widest line's length.

    Each surface cell shows one symbol, so wide characters (such as CJK) become two spaces, keeping later columns
    aligned, and anything that can't be drawn on its own in one cell becomes a space.
    """
    lines = []
    for line in text.splitlines() or [" "]:
        cells = []
        for symbol in line:
            try:
                width = get_symbol_cell_width(symbol)
            except InvalidSymbolError:
                width = 1
                symbol = " "  # noqa: PLW2901
            cells.append(symbol if width == 1 else " " * width)
        lines.append("".join(cells))
    return lines, max(1, *(len(line) for line in lines))


def depth_order(depth: float, distance: float) -> float:
    """Return the order within a layer at `depth`: nearer than the text plane paints later, farther earlier."""
    return max(-0.49, min(0.49, (distance - depth) / (4 * distance)))


class _Slot:
    """One pooled character showing a drawn cell, and the appearance it was last given."""

    __slots__ = ("character", "colors", "frame", "order", "symbol", "visual")

    def __init__(self, character: EffectCharacter) -> None:
        self.character = character
        self.symbol = ""
        self.colors: ColorPair | None = None
        self.visual: object = None
        self.order = math.nan
        self.frame = -1


_Cell = tuple[float, "g3.Vec3 | None", str, ColorPair, "Body"]
"""A drawn cell: its camera depth, the face's world normal (`None` for wireframe edges), symbol, colors and body."""


def _offer(
    cells: dict[Coord, _Cell],
    cell: Coord,
    depth: float,
    normal: g3.Vec3 | None,
    symbol: str,
    colors: ColorPair,
    body: Body,
) -> None:
    """Put a drawn cell into `cells` if it is nearer than what is there."""
    current = cells.get(cell)
    if current is None or depth < current[0]:
        cells[cell] = (depth, normal, symbol, colors, body)


class Painter:
    """Draws a world's drawn bodies with pooled characters, once per frame after the characters move."""

    def __init__(self, world: World, terminal: Terminal) -> None:
        self.world = world
        # Weak, so characters kept after their terminal is gone don't keep it alive through their world.
        self._terminal = weakref.ref(terminal)
        self.frame = 0
        self._slots: dict[Coord, _Slot] = {}
        self._shown: list[_Slot] = []
        self._pairs: dict[Color, ColorPair] = {}
        self._input_text: str | None = None

    @property
    def terminal(self) -> Terminal:
        """The terminal the pooled characters belong to."""
        terminal = self._terminal()
        if terminal is None:  # pragma: no cover - a terminal outlives its own frames
            msg = "The terminal this world draws on is gone."
            raise RuntimeError(msg)
        return terminal

    @property
    def input_text(self) -> str:
        """The effect's input text, top line first, as `Textured` looks wrap it by default."""
        if self._input_text is None:
            characters = self.terminal.get_characters()
            rows: dict[int, dict[int, str]] = {}
            for character in characters:
                rows.setdefault(character.input_coord.row, {})[character.input_coord.column] = character.input_symbol
            left = min((character.input_coord.column for character in characters), default=0)
            right = max((character.input_coord.column for character in characters), default=-1)
            lines = []
            # Every row from top to bottom, so blank input lines stay in the texture.
            for row in range(max(rows, default=-1), min(rows, default=0) - 1, -1):
                symbols, column, line = [], left, rows.get(row, {})
                while column <= right:
                    symbol = line.get(column, " ")
                    symbols.append(symbol)
                    # A wide character already spans the next column, so that column adds nothing.
                    column += get_symbol_cell_width(symbol)
                lines.append("".join(symbols).rstrip())
            self._input_text = "\n".join(lines)
        return self._input_text

    def pair(self, color: Color) -> ColorPair:
        """Return a shared foreground `ColorPair` for `color`, so unchanged cells can be spotted by identity."""
        pair = self._pairs.get(color)
        if pair is None:
            pair = self._pairs[color] = ColorPair(fg=color)
        return pair

    def surface_characters(self) -> dict[Coord, EffectCharacter]:
        """Every pooled character, shown or not, by cell."""
        return {cell: slot.character for cell, slot in self._slots.items()}

    def hide(self, body: Body) -> None:
        """Hide a body's cells now, for a body that stops being drawn or leaves the world."""
        for slot in body._cells:
            self.terminal.set_character_visibility(slot.character, is_visible=False)
        removed = {id(slot) for slot in body._cells}
        self._shown = [slot for slot in self._shown if id(slot) not in removed]
        body._cells = []

    def paint(self) -> None:
        """Draw every drawn body into one depth buffer and show it with the pooled characters."""
        self.frame += 1
        world = self.world
        drawn = [body for body in world._bodies if body._look is not None or body._face_looks]
        if not drawn and not self._shown:
            return
        cells: dict[Coord, _Cell] = {}
        bounds = g3.Bounds.for_canvas(self.terminal.canvas)
        for body in drawn:
            body._cells = []
            self._contribute(body, cells, bounds)
        camera = world.camera
        distance = camera.distance
        frame = self.frame
        decals = self._decals(cells)
        shown: list[_Slot] = []
        for cell, (depth, _normal, symbol, colors, body) in cells.items():
            slot = self._slots.get(cell)
            if slot is None:
                slot = self._slots[cell] = _Slot(self._new_character(cell))
            character = slot.character
            animation = character.animation
            if (
                slot.symbol != symbol
                or slot.colors is not colors
                or slot.visual is not animation.current_character_visual
            ):
                animation.set_appearance(symbol, colors)
                slot.symbol, slot.colors, slot.visual = symbol, colors, animation.current_character_visual
            order = depth_order(decals.get(cell, depth), distance) - _SURFACE_BIAS
            if slot.order != order:
                character._set_depth_order(order)
                slot.order = order
            if not character.is_visible:
                self.terminal.set_character_visibility(character, is_visible=True)
            slot.frame = frame
            body._cells.append(slot)
            shown.append(slot)
        for slot in self._shown:
            if slot.frame != frame:
                self.terminal.set_character_visibility(slot.character, is_visible=False)
        self._shown = shown

    def _new_character(self, cell: Coord) -> EffectCharacter:
        """Add a character that stays on its screen cell whatever the camera does."""
        from terminaltexteffects.engine.motion import ScreenMotion  # noqa: PLC0415 (motion imports this module)

        character = self.terminal.add_character(" ", cell)
        character.motion = ScreenMotion(character)
        return character

    def _decals(self, cells: dict[Coord, _Cell]) -> dict[Coord, float]:
        """Return the depths to order drawn cells at, where a character on the body's surface draws over them.

        A character at height 0 on a drawn body, facing the camera, draws over the body's own cell beneath it, even
        when it measures a little farther (a curved surface is drawn with flat facets). A cell of anything else,
        or of the body well in front of the character, keeps its depth and still hides it.
        """
        decals: dict[Coord, float] = {}
        for body in {cell[4] for cell in cells.values()}:
            surface = body._surface
            if surface is None:
                continue
            for node in body._children:
                if not node._ON_SURFACE:
                    continue  # a body: only characters are decals
                character = typing.cast("EffectCharacter", node)
                if not character.is_visible or character.motion._xyz[2]:
                    continue
                view = character.view
                if not view.projected or not view.facing:
                    continue
                cell = view.cell
                drawn = cells.get(cell)
                if drawn is None or drawn[4] is not body or not 0 < view.depth - drawn[0] <= _DECAL_REACH:
                    continue
                decals[cell] = max(decals.get(cell, drawn[0]), view.depth)
        return decals

    def _contribute(self, body: Body, cells: dict[Coord, _Cell], bounds: g3.Bounds) -> None:
        """Add the body's nearest surface in each cell inside `bounds` to `cells`, where it beats what is there."""
        mesh = body.mesh
        if mesh is None:
            return
        world = self.world
        camera = world.camera
        pose = {
            "rotation": body.world_rotation,
            "scale": body.world_scale,
            "position": body.world_position,
            "bounds": bounds,
        }
        look = body._look
        if isinstance(look, Wireframe):
            front = self.pair(look.color)
            hidden = self.pair(look.hidden_color) if look.hidden_color is not None else None
            for cell, edge in g3.wireframe(mesh, camera, depth_test=look.depth_test, **pose).items():
                if edge.front:
                    _offer(cells, cell, edge.depth, None, edge.symbol, front, body)
                elif hidden is not None:
                    _offer(cells, cell, edge.depth, None, edge.symbol, hidden, body)
            return
        two_sided = any(
            isinstance(each, Textured) and each.back == "dim" for each in (body._look, *body._face_looks.values())
        )
        if two_sided:
            fronts, backs = g3._rasterize_sides(mesh, camera, **pose)
        else:
            fronts, backs = g3.rasterize(mesh, camera, cull="back", **pose), {}
        # Shading depends only on the face, so it is worked out once per face rather than per cell.
        styles: dict[int, tuple[Look | None, str, ColorPair, ColorPair]] = {}
        for cell, fragment in fronts.items():
            style = styles.get(fragment.face)
            if style is None:
                style = styles[fragment.face] = self._face_style(body, fragment)
            face_look, symbol, colors, fallback = style
            if face_look is None:
                continue
            if isinstance(face_look, Textured):
                sampled = self._sample(body, face_look, fragment)
                if sampled is None:
                    colors = fallback  # A face without a texture layout is shaded instead.
                elif sampled == " " and face_look.back == "dim":
                    continue  # Let the far side show through.
                else:
                    symbol = sampled
            _offer(cells, cell, fragment.depth, fragment.normal, symbol, colors, body)
        for cell, fragment in backs.items():
            face_look = body._face_look(fragment.tag)
            if isinstance(face_look, Textured) and face_look.back == "dim":
                symbol = self._sample(body, face_look, fragment) or " "
                _offer(cells, cell, fragment.depth, fragment.normal, symbol, self.pair(face_look.back_color), body)

    def _face_style(self, body: Body, fragment: g3.Fragment) -> tuple[Look | None, str, ColorPair, ColorPair]:
        """Return a face's look, symbol, lit colors and colors for untextured faces, from its angle to the light."""
        look = body._face_look(fragment.tag)
        shade = g3.lambert(fragment.normal, self.world.world_light)
        lit = _AMBIENT + (1 - _AMBIENT) * shade
        ramp = _SHADE_SYMBOLS[min(len(_SHADE_SYMBOLS) - 1, int(shade * len(_SHADE_SYMBOLS)))]
        if isinstance(look, Shaded):
            symbol = look.symbols[min(len(look.symbols) - 1, int(shade * len(look.symbols)))]
            colors = self.pair(_gradient(look.gradient).get_color_at_fraction(shade))
            return look, symbol, colors, colors
        if isinstance(look, Solid):
            colors = self.pair(_gradient(look.gradient).get_color_at_fraction(lit))
            return look, look.symbol, colors, colors
        if isinstance(look, Textured):
            colors = self.pair(_gradient(look.gradient).get_color_at_fraction(lit))
            return look, ramp, colors, self.pair(look.back_color)
        return None, ramp, self.pair(_DIM), self.pair(_DIM)

    def _sample(self, body: Body, look: Textured, fragment: g3.Fragment) -> str | None:
        """Return the text symbol at a fragment, or `None` where its face has no texture layout."""
        shape = body.shape
        place = shape.texture_cell(fragment) if shape is not None else None
        if place is None:
            return None
        texts = body._texts
        grid = texts.get(id(look))
        if grid is None:
            grid = texts[id(look)] = _text_grid(look.text if look.text is not None else self.input_text)
        lines, width = grid
        # The nudge keeps cells that land exactly on a text column boundary from rounding down a column.
        row = math.floor(
            place[1] * g3.TERMINAL_ROW_SCALE / self.world.camera.row_scale / look.scale + look.offset[1] + _TEXT_NUDGE
        )
        column = math.floor(place[0] / look.scale + look.offset[0] + _TEXT_NUDGE)
        if look.repeat:
            row, column = row % len(lines), column % width
        else:
            row, column = min(max(row, 0), len(lines) - 1), min(max(column, 0), width - 1)
        line = lines[row]
        return line[column] if column < len(line) else " "
