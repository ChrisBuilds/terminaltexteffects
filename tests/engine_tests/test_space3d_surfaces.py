"""Tests for drawing `Space3D` bodies as filled surfaces with looks."""

from __future__ import annotations

import typing
from dataclasses import replace

import pytest

from terminaltexteffects.engine import space3d
from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.utils import geometry3d as g3
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.graphics import Color, ColorPair, Gradient

if typing.TYPE_CHECKING:
    from terminaltexteffects.engine.base_character import EffectCharacter

pytestmark = [pytest.mark.engine, pytest.mark.smoke]

TEXT = "Hello TTE\nsurfaces!\n0123456789"


def make_space(text: str = TEXT, width: int = 41, height: int = 21, **settings: object) -> space3d.Space3D:
    """Build an orthographic space on a fresh terminal, so drawn cells are easy to predict."""
    config = TerminalConfig._build_config()
    config.frame_rate = 0
    config.canvas_width = width
    config.canvas_height = height
    settings.setdefault("perspective", 0)
    return space3d.Space3D(Terminal(text, config=config), **settings)  # type: ignore[arg-type]


def symbol(character: EffectCharacter) -> str:
    """Return the symbol a character currently shows."""
    return character.animation.current_character_visual.symbol


def color(character: EffectCharacter) -> Color | None:
    """Return the foreground color a character currently shows."""
    colors = character.animation.current_character_visual.colors
    return colors.fg if colors is not None else None


def rows(body: space3d.Body) -> list[str]:
    """Return the body's drawn cells as text, top row first, trimmed to the drawn columns."""
    cells = body.surface_characters
    columns = [cell.column for cell in cells]
    lines = []
    for row in sorted({cell.row for cell in cells}, reverse=True):
        line = "".join(
            symbol(cells[Coord(column, row)]) if Coord(column, row) in cells else " "
            for column in range(min(columns), max(columns) + 1)
        )
        lines.append(line)
    return lines


# Drawing and erasing


def test_draw_needs_a_shape_and_rejects_per_face_wireframes() -> None:
    """Draw needs a shape, and a wireframe can't be given per face."""
    space = make_space()
    with pytest.raises(ValueError, match="shape"):
        space.body().draw()
    with pytest.raises(ValueError, match="Wireframe"):
        space.body(space3d.Cube(10)).draw(faces={0: space3d.Wireframe()})
    with pytest.raises(ValueError, match="Wireframe"):
        space.body(space3d.Cube(10)).draw(space3d.Wireframe(), faces={0: space3d.Solid()})


def test_wireframe_depth_test_omits_occluded_edges_when_hidden_color_is_none() -> None:
    """The body look forwards its opt-in depth test and suppresses hidden cells."""
    space = make_space(width=81, height=41, perspective=0)
    body = space.body(space3d.Torus(20, 8, 36, 18)).draw(space3d.Wireframe(hidden_color=None, depth_test=True))
    space.step()
    assert body.mesh is not None
    edges = g3.wireframe(body.mesh, space.camera, depth_test=True, bounds=g3.Bounds.for_canvas(space.terminal.canvas))
    assert set(body.surface_characters) == {cell for cell, edge in edges.items() if edge.front}


def test_looks_validate_their_settings() -> None:
    """Looks validate their settings."""
    with pytest.raises(ValueError, match="symbol"):
        space3d.Shaded(symbols="")
    with pytest.raises(ValueError, match="back"):
        space3d.Textured(back="show")  # type: ignore[arg-type]
    for bad in ("界", "ab", "\t"):
        with pytest.raises(ValueError, match="one cell wide"):
            space3d.Solid(bad)
    for bad in ("界", "\t"):
        with pytest.raises(ValueError, match="one cell wide"):
            space3d.Shaded(symbols=f".{bad}")


def test_draw_defaults_to_shaded_and_fills_the_projected_shape() -> None:
    """With no look, a body is shaded, and a front-on cube fills its projected square."""
    space = make_space()
    body = space.body(space3d.Cube(10)).draw()
    assert body.drawn
    assert body.surface_characters == {}  # Nothing is drawn until the space steps.
    space.step()
    cells = body.surface_characters
    columns = {cell.column for cell in cells}
    rows_drawn = {cell.row for cell in cells}
    assert columns == set(range(16, 27))
    assert rows_drawn == set(range(9, 14))
    assert len(cells) == len(columns) * len(rows_drawn)
    assert all(symbol(character) in ".,-~:;=!*#$@" for character in cells.values())


def test_remove_and_clear_hide_surfaces_immediately_and_reuse_pool() -> None:
    """Removal hides owned surface slots immediately; later bodies can reuse the space pool."""
    space = make_space()
    first = space.body(space3d.Cube(8)).draw()
    second = space.body(space3d.Cube(8), at=(12, 0, 0)).draw()
    space.step()
    old_cells = list(first.surface_characters.values())
    other_cells = list(second.surface_characters.values())
    assert old_cells
    assert other_cells
    space.remove(first)
    assert not first.surface_characters
    assert not first.drawn
    assert all(not cell.is_visible for cell in old_cells)
    assert all(cell.is_visible for cell in other_cells)
    space.clear()
    assert not space.bodies
    assert not space.mounts
    assert all(not cell.is_visible for cell in space.surface_characters.values())
    third = space.body(space3d.Cube(8)).draw()
    space.step()
    assert set(third.surface_characters.values()) == set(old_cells)
    assert all(cell.is_visible for cell in old_cells)


def test_erase_hides_the_cells_at_the_next_step() -> None:
    """Erase hides the body's cells at the next step and keeps the pooled characters."""
    space = make_space()
    body = space.body(space3d.Cube(10)).draw()
    space.step()
    drawn = list(body.surface_characters.values())
    assert all(character.is_visible for character in drawn)
    body.erase()
    assert not body.drawn
    space.step()
    assert body.surface_characters == {}
    assert not any(character.is_visible for character in drawn)
    assert set(space.surface_characters.values()) >= set(drawn)


def test_pooled_characters_are_reused_and_cells_left_behind_are_hidden() -> None:
    """Pooled characters stay put and are reused, and cells a moving body leaves are hidden."""
    space = make_space()
    body = space.body(space3d.Cube(6)).draw()
    space.step()
    first = dict(body.surface_characters)
    body.move_by(3, 0, 0)
    space.step()
    second = body.surface_characters
    shared = first.keys() & second.keys()
    assert shared
    assert all(first[cell] is second[cell] for cell in shared)
    for cell in first.keys() - second.keys():
        assert not first[cell].is_visible
    for cell, character in second.items():
        assert character.input_coord == cell
        assert character.is_visible
    assert len(space.surface_characters) == len(first.keys() | second.keys())


def test_surface_characters_are_added_characters_not_input_characters() -> None:
    """Surfaces are drawn with characters the space adds, never the effect's input characters."""
    space = make_space()
    body = space.body(space3d.Cube(10)).draw()
    space.step()
    added = set(space.terminal.get_characters(added_chars=True)) - set(space.terminal.get_characters())
    assert set(body.surface_characters.values()) <= added


def test_cells_outside_the_canvas_are_not_drawn() -> None:
    """Cells outside the canvas are not drawn."""
    space = make_space()
    body = space.body(space3d.Cube(20), at=(18, 0, 0)).draw()
    space.step()
    canvas = space.terminal.canvas
    cells = body.surface_characters
    assert cells
    assert max(cell.column for cell in cells) == canvas.right


def test_an_effect_restyle_lasts_until_the_next_step() -> None:
    """A change the effect makes to a surface character lasts until the next step redraws it."""
    space = make_space()
    body = space.body(space3d.Cube(10)).draw(space3d.Solid("#"))
    space.step()
    character = body.surface_characters[Coord(21, 11)]
    character.animation.set_appearance("X")
    assert symbol(character) == "X"
    space.step()
    assert symbol(character) == "#"


# Looks


def test_shaded_faces_brighten_toward_the_light() -> None:
    """Shaded picks a later symbol and gradient color for a face turned more toward the light."""
    gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=10)
    space = make_space(light="front")
    square = space.body(space3d.Cube(6), at=(-10, 0, 0)).draw(space3d.Shaded(gradient, symbols="abcd"))
    turned = space.body(space3d.Cube(10), at=(8, 0, 0)).rotate("y", 25)
    turned.draw(space3d.Shaded(gradient, symbols="abcd"))
    space.step()
    facing = square.surface_characters[Coord(11, 11)]
    assert symbol(facing) == "d"
    assert color(facing) == Color("#ffffff")
    # The front face is 25 degrees from the light and the side face 65, so the side is darker.
    by_symbol = {symbol(character): color(character) for character in turned.surface_characters.values()}
    assert set(by_symbol) == {"b", "d"}
    assert by_symbol["b"] != by_symbol["d"]


def test_solid_uses_one_symbol_with_ambient_light() -> None:
    """Solid draws one symbol, and a face turned from the light still gets some color."""
    gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=20)
    space = make_space(light="left")
    body = space.body(space3d.Cube(10)).draw(space3d.Solid("@", gradient))
    space.step()
    characters = body.surface_characters.values()
    assert {symbol(character) for character in characters} == {"@"}
    assert all(color(character) != Color("#000000") for character in characters)


def test_default_gradient_uses_the_brand_colors() -> None:
    """Looks without a gradient color fully lit faces with the last brand color."""
    space = make_space(light="front")
    body = space.body(space3d.Cube(10)).draw(space3d.Solid())
    space.step()
    assert color(body.surface_characters[Coord(21, 11)]) == Color("#ffffff")


@pytest.mark.parametrize("row_scale", [1.0, 2.0, 3.0])
def test_textured_row_density_follows_camera(row_scale: float) -> None:
    """Each projected terminal row samples the corresponding texture row for any cell ratio."""
    space = make_space()
    space.camera.row_scale = row_scale
    body = space.body(space3d.Box(8, 12, 4)).draw(space3d.Textured("AAAA\nBBBB\nCCCC\nDDDD"))
    space.step()
    center = space.camera.center_row
    top = center + 6 / row_scale
    for coord, character in body.surface_characters.items():
        expected_row = int((top - coord.row) + 1e-7) % 4
        assert symbol(character) == "ABCD"[expected_row]


@pytest.mark.parametrize(
    ("look", "expected"),
    [
        (space3d.Textured("ABCD\nEFGH", offset=(1, 1)), "G"),
        (space3d.Textured("ABCD\nEFGH", offset=(-2, -1)), "H"),
        (space3d.Textured("ABCD\nEFGH", scale=2), "A"),
        (space3d.Textured("ABCD\nEFGH", offset=(100, 100), repeat=False), "H"),
        (space3d.Textured("ABCD\nEFGH", offset=(-100, -100), repeat=False), "A"),
    ],
)
def test_texture_controls_sample_text_without_moving_geometry(look: space3d.Textured, expected: str) -> None:
    """Offset, scale and clamping transform text sampling while leaving the body pose alone."""
    space = make_space()
    body = space.body(space3d.Cube(8)).draw(look)
    fragment = g3.Fragment(1, g3.Z_AXIS, True, 0, 0, (0.125, 1.0))  # noqa: FBT003
    assert body._sample(look, fragment) == expected
    assert body.position == g3.ORIGIN
    assert body.rotation == g3.Rotation()


@pytest.mark.parametrize("scale", [0, -1, float("inf"), float("nan")])
def test_texture_scale_rejects_invalid_values(scale: float) -> None:
    """Invalid text sizes fail when constructing the look."""
    with pytest.raises(ValueError, match="scale"):
        space3d.Textured(scale=scale)


def test_texture_offset_can_be_animated_by_replacing_the_look() -> None:
    """Replacing an immutable look scrolls the text without changing surface coordinates or body pose."""
    space = make_space()
    look = space3d.Textured("ABCD")
    body = space.body(space3d.Cube(8)).draw(look)
    space.step()
    before = {coord: symbol(character) for coord, character in body.surface_characters.items()}
    body.draw(replace(look, offset=(1, 0)))
    space.step()
    after = {coord: symbol(character) for coord, character in body.surface_characters.items()}
    assert after.keys() == before.keys()
    assert all(after[coord] == "BCDA"["ABCD".index(value)] for coord, value in before.items())
    assert body.rotation == g3.Rotation()


def test_textured_cube_shows_the_input_text_on_its_front_face() -> None:
    """A front-on textured cube shows the input text from the face's top left corner."""
    space = make_space()
    body = space.body(space3d.Box(10, 6, 10)).draw(space3d.Textured())
    space.step()
    assert rows(body) == ["Hello TTE H", "surfaces! s", "01234567890"]
    assert space.input_text == TEXT


def test_textured_text_can_be_any_string_and_repeats() -> None:
    """A textured look can wrap any string, and repeats it across a larger face."""
    space = make_space()
    body = space.body(space3d.Box(10, 4, 10)).draw(space3d.Textured("ab\ncd"))
    space.step()
    assert rows(body) == ["abababababa", "cdcdcdcdcdc", "abababababa"]


def test_textured_faces_without_a_layout_are_shaded_in_the_back_color() -> None:
    """Faces with no texture layout, such as a cylinder's cap, are shaded in the back color."""
    space = make_space()
    back = Color("#123456")
    body = space.body(space3d.Cylinder(8, 6)).rotate("x", 90).draw(space3d.Textured(back_color=back))
    space.step()
    characters = list(body.surface_characters.values())
    assert characters
    assert all(color(character) == back for character in characters)
    assert all(symbol(character) in ".,-~:;=!*#$@" for character in characters)


def test_textured_dim_shows_the_far_side_through_gaps() -> None:
    """With `back="dim"`, spaces in the text show the far side in the back color."""
    space = make_space()
    back = Color("#123456")
    hide = space.body(space3d.Cylinder(8, 6), at=(-10, 0, 0)).draw(space3d.Textured("a b c d e f g h"))
    dim = space.body(space3d.Cylinder(8, 6), at=(10, 0, 0)).draw(
        space3d.Textured("a b c d e f g h", back="dim", back_color=back)
    )
    space.step()
    hidden = hide.surface_characters.values()
    dimmed = dim.surface_characters.values()
    assert " " in {symbol(character) for character in hidden}
    assert all(color(character) != back for character in hidden if symbol(character) != " ")
    assert any(color(character) == back for character in dimmed)
    assert {symbol(character) for character in dimmed if color(character) != back} <= set("abcdefgh")


def test_shapes_map_their_faces_into_the_text() -> None:
    """Each shape with a texture layout maps its faces into the text, and others don't."""
    fragment = g3.Fragment(1.0, g3.Z_AXIS, True, 0, 0, (0.5, 1.0))  # noqa: FBT003
    no_uv = fragment._replace(uv=None)
    assert space3d.Box(10, 6, 8).texture_cell(fragment) == (5.0, 0.0)
    assert space3d.Box(10, 6, 8).texture_cell(fragment._replace(tag=1)) == (4.0, 0.0)
    assert space3d.Cube(10).texture_cell(fragment) == (5.0, 0.0)
    for shape in (space3d.Prism(), space3d.Pyramid(), space3d.Cylinder(), space3d.Sphere()):
        place = shape.texture_cell(fragment)
        assert place is not None
        assert place[1] == 0.0
        assert shape.texture_cell(no_uv) is None
    assert space3d.Torus().texture_cell(fragment) is None
    assert space3d.Tetrahedron().texture_cell(fragment) is None
    bottom = space3d.Cylinder(10, 8).texture_cell(fragment._replace(uv=(0.0, 0.0)))
    assert bottom == pytest.approx((2 * 3.141592653589793 * 10 / 4, 8 / g3.TERMINAL_ROW_SCALE))


def test_wireframe_draws_edges_with_hidden_edges_dimmed_or_left_out() -> None:
    """Wireframe draws edge symbols, with hidden edges in the hidden color or left out."""
    front, hidden = Color("#00ff00"), Color("#ff0000")
    space = make_space()
    shown = space.body(space3d.Cube(10), at=(-10, 0, 0)).rotate("y", 30).rotate("x", 20)
    shown.draw(space3d.Wireframe(front, hidden))
    left_out = space.body(space3d.Cube(10), at=(10, 0, 0)).rotate("y", 30).rotate("x", 20)
    left_out.draw(space3d.Wireframe(front, None))
    space.step()
    shown_colors = {color(character) for character in shown.surface_characters.values()}
    assert shown_colors == {front, hidden}
    assert {color(character) for character in left_out.surface_characters.values()} == {front}
    assert {symbol(character) for character in shown.surface_characters.values()} <= set("-/|\\")


def test_per_face_looks_draw_only_their_faces() -> None:
    """Looks given per face draw those faces, and others are left out without a body look."""
    space = make_space()
    body = space.body(space3d.Cube(10)).rotate("y", 30).draw(faces={0: space3d.Solid("A")})
    space.step()
    assert {symbol(character) for character in body.surface_characters.values()} == {"A"}
    body.draw(space3d.Solid("B"), faces={0: space3d.Solid("A")})
    space.step()
    assert {symbol(character) for character in body.surface_characters.values()} == {"A", "B"}


# Depth and layers


def test_bodies_share_one_depth_buffer() -> None:
    """Where bodies overlap, the nearer one is drawn and the farther one shows only around it."""
    space = make_space()
    far = space.body(space3d.Cube(12), at=(0, 0, -20)).draw(space3d.Solid("F"))
    near = space.body(space3d.Cube(6), at=(0, 0, 10)).draw(space3d.Solid("N"))
    space.step()
    assert Coord(21, 11) in near.surface_characters
    assert Coord(21, 11) not in far.surface_characters
    assert far.surface_characters
    assert not far.surface_characters.keys() & near.surface_characters.keys()


def painter_order(character: EffectCharacter) -> tuple[int, float]:
    """Return what the terminal orders characters by within a cell, ahead of creation order."""
    return character.layer, character._depth_order


def test_surface_cells_layer_by_depth_just_below_mounted_characters() -> None:
    """Surface cells are ordered by depth, just below a character mounted at the same depth."""
    space = make_space()
    body = space.body(space3d.Box(10, 6, 10)).draw()
    character = space.terminal.get_characters()[0]
    space.mount(character, body.anchor(0, 0, 5))
    space.step()
    character.tick()
    cell = body.surface_characters[character.motion.current_coord]
    assert painter_order(cell) < painter_order(character)
    assert cell.layer == character.layer
    layer = cell.layer
    body.move_by(0, 0, 10)
    space.step()
    assert body.surface_characters[Coord(21, 11)].layer == layer + 10


def test_surface_slightly_nearer_than_mounted_text_draws_over_it() -> None:
    """A surface cell a fraction of a column nearer than a mounted character is drawn over it."""
    space = make_space()
    body = space.body(space3d.Box(10, 6, 10)).draw()
    character = space.terminal.get_characters()[0]
    space.mount(character, space.body().anchor(0, 0, 4.7))
    space.step()
    character.tick()
    cell = body.surface_characters[character.motion.current_coord]
    assert painter_order(cell) > painter_order(character)


def test_draw_mounted_text_reads_over_its_surface_in_the_frame() -> None:
    """A mounted character shows over the surface cell it sits on in the rendered frame."""
    space = make_space("Z")
    body = space.body(space3d.Box(10, 6, 10)).draw(space3d.Solid("#"))
    character = space.terminal.get_characters()[0]
    space.terminal.set_character_visibility(character, is_visible=True)
    space.mount(character, body.anchor(0, 0, 5))
    space.step()
    character.tick()
    frame = space.terminal.get_formatted_output_string()
    assert "Z" in frame
    assert "#" in frame


@pytest.mark.parametrize("perspective", [0, 1, 0.0001])
@pytest.mark.parametrize(
    ("axis", "angle", "offset"),
    [
        ("y", 15, (0, 0, 0)),
        ("y", -40, (3, 0, 0)),
        ("x", 25, (0, 2, 0)),
        ("diagonal", 30, (-4, 1, 5)),
        ("y", 70, (0, 0, -8)),
    ],
)
def test_text_mounted_on_a_turned_face_reads_over_it(
    perspective: float, axis: str, angle: float, offset: tuple[float, float, float]
) -> None:
    """Text on a slanted front face shows over that face, though the face is measured at the cell center."""
    space = make_space("Z", perspective=perspective)
    character = space.terminal.get_characters()[0]
    space.terminal.set_character_visibility(character, is_visible=True)
    body = space.body(space3d.Cube(12), at=offset).rotate(axis, angle).draw(space3d.Solid("#"))
    space.mount(character, body.anchor(2, 0, 6))
    space.step()
    character.tick()
    cell = body.surface_characters[character.motion.current_coord]
    assert painter_order(cell) < painter_order(character)
    assert "Z" in space.terminal.get_formatted_output_string()


@pytest.mark.parametrize("perspective", [0, 1, 0.0001])
def test_a_nearer_surface_covers_text_on_a_turned_face(perspective: float) -> None:
    """A surface a fraction of a column in front of a slanted face still covers the text mounted on that face."""
    space = make_space("Z", perspective=perspective)
    character = space.terminal.get_characters()[0]
    body = space.body(space3d.Cube(12)).rotate("y", 15)
    anchor = body.anchor(2, 0, 6, normal="z")
    space.mount(character, anchor)
    space.step()
    character.tick()
    cell = character.motion.current_coord
    shield = space.body(space3d.Box(4, 4, 2)).draw(space3d.Solid("#"))
    # Turned like the face and moved so its front sits 0.2 columns in front of the anchor, along the face normal.
    shield.rotate("y", 15)
    normal = body.rotation.apply(g3.Z_AXIS)
    center = anchor.world_point() + normal * (0.2 - 1.0)
    shield.set_position(center.x, center.y, center.z)
    space.step()
    character.tick()
    assert painter_order(shield.surface_characters[cell]) > painter_order(character)


def test_text_on_a_far_face_stays_behind_the_near_face() -> None:
    """Text on a body's back face does not show through the front face covering it."""
    space = make_space("Z")
    character = space.terminal.get_characters()[0]
    body = space.body(space3d.Cube(12)).rotate("y", 15).draw(space3d.Solid("#"))
    space.mount(character, body.anchor(1, 0, -6))
    space.step()
    character.tick()
    cell = body.surface_characters[character.motion.current_coord]
    assert painter_order(cell) > painter_order(character)


def test_unchanged_cells_keep_their_visual() -> None:
    """Cells whose symbol and color don't change keep the same visual between steps."""
    space = make_space()
    body = space.body(space3d.Cube(10)).draw(space3d.Solid())
    space.step()
    visuals = {
        cell: character.animation.current_character_visual for cell, character in body.surface_characters.items()
    }
    space.step()
    for cell, character in body.surface_characters.items():
        assert character.animation.current_character_visual is visuals[cell]
    pair = space._pair(Color("#abcdef"))
    assert pair == ColorPair(fg=Color("#abcdef"))
    assert space._pair(Color("#abcdef")) is pair


def test_a_far_body_shows_behind_the_far_side_seen_through_text_gaps() -> None:
    """Through a gap in dim text, the body's own far side is nearer than a body behind it, so it wins."""
    space = make_space()
    back = Color("#123456")
    hollow = space.body(space3d.Cylinder(8, 8)).draw(space3d.Textured(" ", back="dim", back_color=back))
    behind = space.body(space3d.Cube(6), at=(0, 0, -40)).draw(space3d.Solid("#"))
    space.step()
    center = hollow.surface_characters[Coord(21, 11)]
    assert color(center) == back
    assert Coord(21, 11) not in behind.surface_characters


def test_textured_text_keeps_every_drawn_symbol_one_cell_wide() -> None:
    """Wide characters become two blank cells and symbols that can't be drawn alone become one."""
    space = make_space()
    body = space.body(space3d.Box(10, 2, 10)).draw(space3d.Textured("a界b\tc"))
    space.step()
    assert rows(body)[0].startswith("a  b c")
    assert space3d._text_grid("a界b\tc") == (["a  b c"], 6)


def test_input_text_counts_a_wide_character_once() -> None:
    """The default text keeps input columns: a wide character's second column adds no extra gap."""
    space = make_space("a界b\nxyz")
    assert space.input_text == "a界b\nxyz"
    assert space3d._text_grid(space.input_text)[0] == ["a  b", "xyz"]


def test_input_text_keeps_blank_lines() -> None:
    """A blank line inside the input stays in the default text, so later rows keep their place."""
    space = make_space("a\n\nb")
    assert space.input_text == "a\n\nb"
