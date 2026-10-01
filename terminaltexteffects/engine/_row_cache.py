"""Opt-in terminal row caching and character change tracking."""

from __future__ import annotations

import typing
import weakref
from dataclasses import dataclass

from terminaltexteffects.engine.animation import Animation, CharacterVisual
from terminaltexteffects.engine.motion import Motion

if typing.TYPE_CHECKING:
    from terminaltexteffects.engine.base_character import EffectCharacter
    from terminaltexteffects.engine.terminal import Terminal
    from terminaltexteffects.utils.geometry import Coord


@dataclass(eq=False)
class _RenderRecord:
    """Keep directly readable render state without retaining the owning terminal."""

    character: EffectCharacter
    coord: Coord
    visual: CharacterVisual
    cache: weakref.ReferenceType[RowCache]


class _TrackedMotion(Motion):
    """Observe coordinate assignments only for characters in a cached terminal."""

    _render_record: _RenderRecord

    @property
    def current_coord(self) -> Coord:
        """Return the current coordinate from the character's render record."""
        return self._render_record.coord

    @current_coord.setter
    def current_coord(self, value: Coord) -> None:  # pyright: ignore[reportIncompatibleVariableOverride]
        record = self._render_record
        previous = record.coord
        record.coord = value
        if previous != value and (cache := record.cache()) is not None:
            cache.coordinate_changed(record, previous)


class _TrackedAnimation(Animation):
    """Observe visual replacements only for characters in a cached terminal."""

    _render_record: _RenderRecord

    @property
    def current_character_visual(self) -> CharacterVisual:
        """Return the current visual from the character's render record."""
        return self._render_record.visual

    @current_character_visual.setter
    def current_character_visual(self, value: CharacterVisual) -> None:
        record = self._render_record
        previous = record.visual
        record.visual = value
        if previous._formatted_symbol != value._formatted_symbol and (cache := record.cache()) is not None:
            cache.visual_changed(record)


def _painter_key(record: _RenderRecord) -> tuple[int, int]:
    return record.character.layer, record.character.character_id


class RowCache:
    """Cache formatted rows and per-row painter order for an opted-in terminal.

    Normal character changes invalidate their affected rows. Direct edits to a
    `CharacterVisual.formatted_symbol` conservatively invalidate every cached row.
    Tracking preserves the identity of each character's motion and animation objects.
    """

    def __init__(self, terminal: Terminal) -> None:
        self._terminal = weakref.ref(terminal)
        self._records: dict[EffectCharacter, _RenderRecord] = {}
        self._geometry: tuple[int, int, int, int, int, int, str] | None = None
        self._members: list[set[_RenderRecord]] = []
        self._orders: list[list[_RenderRecord] | None] = []
        self._rows: list[str] = []
        self._dirty: set[int] = set()
        self._format_generation = CharacterVisual._format_generation
        self._was_wide = False

    def track(self, character: EffectCharacter) -> None:
        """Promote tracking in place so paths, callbacks and external references remain valid."""
        if character in self._records:
            return
        record = _RenderRecord(
            character,
            character.motion.current_coord,
            character.animation.current_character_visual,
            weakref.ref(self),
        )
        self._records[character] = record
        # These subclasses have the same object layout as their bases. Promotion
        # retains references acquired before caching was enabled.
        character.motion.__dict__["_render_record"] = record
        character.motion.__dict__.pop("current_coord")
        character.motion.__class__ = _TrackedMotion
        character.animation.__dict__["_render_record"] = record
        character.animation.__dict__.pop("current_character_visual")
        character.animation.__class__ = _TrackedAnimation

    @staticmethod
    def _geometry_key(terminal: Terminal) -> tuple[int, int, int, int, int, int, str]:
        return (
            terminal.visible_left,
            terminal.visible_right,
            terminal.visible_bottom,
            terminal.visible_top,
            terminal.canvas_row_offset,
            terminal.canvas_column_offset,
            terminal._blank_row,
        )

    def _mark(
        self,
        record: _RenderRecord,
        coord: Coord,
        *,
        add: bool = False,
        remove: bool = False,
        reorder: bool = False,
    ) -> None:
        terminal = self._terminal()
        if terminal is None or self._geometry != self._geometry_key(terminal):
            return
        row = coord.row + terminal.canvas_row_offset
        if terminal.visible_bottom <= row <= terminal.visible_top:
            index = row - 1
            self._dirty.add(index)
            if add or remove or reorder:
                self._orders[index] = None
            if add:
                self._members[index].add(record)
            if remove:
                self._members[index].discard(record)

    def coordinate_changed(self, record: _RenderRecord, previous: Coord) -> None:
        """Invalidate both footprints of a visible character that moved."""
        if record.character.is_visible:
            self._mark(record, previous, remove=True)
            self._mark(record, record.coord, add=True)

    def visual_changed(self, record: _RenderRecord) -> None:
        """Invalidate a visible character's row after its formatted appearance changes."""
        if record.character.is_visible:
            self._mark(record, record.coord)

    def visibility_changed(self, character: EffectCharacter, *, visible: bool) -> None:
        """Update row membership after a terminal visibility change."""
        record = self._records[character]
        self._mark(record, record.coord, add=visible, remove=not visible)

    def layer_changed(self, character: EffectCharacter) -> None:
        """Invalidate row painter order after a visible character's layer changes."""
        record = self._records[character]
        self._mark(record, record.coord, reorder=True)

    def _reset(self, terminal: Terminal) -> None:
        self._geometry = self._geometry_key(terminal)
        self._members = [set() for _ in range(terminal.visible_top)]
        self._orders = [None] * terminal.visible_top
        self._rows = [terminal._blank_row] * terminal.visible_top
        self._dirty = set(range(terminal.visible_top))
        self._format_generation = CharacterVisual._format_generation
        self._was_wide = False
        for character in terminal._visible_characters:
            record = self._records[character]
            self._mark(record, record.coord, add=True)

    def render(self, terminal: Terminal) -> list[str] | None:
        """Reuse unchanged single-cell rows, returning `None` for width-aware rendering."""
        if self._geometry != self._geometry_key(terminal):
            self._reset(terminal)
        if self._format_generation != CharacterVisual._format_generation:
            self._dirty.update(range(terminal.visible_top))
            self._format_generation = CharacterVisual._format_generation
        if terminal._visible_wide_character_count:
            self._was_wide = True
            return None
        if self._was_wide:
            self._dirty.update(range(terminal.visible_top))
            self._was_wide = False
        for index in self._dirty:
            cells = list(terminal._blank_row)
            records = self._orders[index]
            if records is None:
                records = sorted(self._members[index], key=_painter_key)
                self._orders[index] = records
            for record in records:
                column = record.coord.column + terminal.canvas_column_offset
                if terminal.visible_left <= column <= terminal.visible_right:
                    cells[column - 1] = record.visual._formatted_symbol
            self._rows[index] = "".join(cells)
        self._dirty.clear()
        return self._rows.copy()
