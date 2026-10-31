"""Tests for drawing bodies with looks: the world's pooled cells, looks, and depth against characters."""

from __future__ import annotations

import math
import typing
from dataclasses import replace

import pytest

from terminaltexteffects.engine import drawing
from terminaltexteffects.engine.drawing import Ink, Shaded, Solid, Textured, Wireframe
from terminaltexteffects.engine.shapes import Box, Cube, Cylinder, Prism, Pyramid, Shape, Sphere, Tetrahedron, Torus
from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.utils import geometry3d as g3
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.graphics import Color, ColorPair, Gradient

if typing.TYPE_CHECKING:
    from terminaltexteffects.engine.base_character import EffectCharacter
    from terminaltexteffects.engine.drawing import Painter
    from terminaltexteffects.engine.world import Body, World

pytestmark = [pytest.mark.engine, pytest.mark.smoke]

TEXT = "Hello TTE\nsurfaces!\n0123456789"


def make_world(
    text: str = TEXT, width: int = 41, height: int = 21, perspective: float = 0, light: str = "upper left"
) -> World:
    """Build an orthographic world on a fresh terminal, so drawn cells are easy to predict."""
    config = TerminalConfig._build_config()
    config.frame_rate = 0
    config.canvas_width = width
    config.canvas_height = height
    terminal = Terminal(text, config=config)
    _TERMINALS.append(terminal)  # A world holds its terminal weakly.
    world = terminal.world
    world.camera.set_perspective(perspective)
    world.set_light(light)
    return world


_TERMINALS: list[Terminal] = []


def painter(world: World) -> Painter:
    """Return the world's painter."""
    assert world._painter is not None
    return world._painter


def terminal_of(world: World) -> Terminal:
    """Return the terminal the world draws on."""
    return painter(world).terminal


def step(world: World) -> None:
    """Play one frame as `update()` does, without an effect: step, project the characters again, paint."""
    if world.step():
        terminal_of(world)._project_all_characters()
    world.paint()


def attach(world: World, body: Body, point: tuple[float, float, float]) -> EffectCharacter:
    """Attach the first input character to `body` at a point in its axes, on its surface if it has one."""
    character = terminal_of(world).get_characters()[0]
    terminal_of(world).set_character_visibility(character, is_visible=True)
    character.attach(body, at=body.surface.locate(point) if body.has_surface else point)
    return character


def symbol(character: EffectCharacter) -> str:
    """Return the symbol a character currently shows."""
    return character.animation.current_character_visual.symbol


def color(character: EffectCharacter) -> Color | None:
    """Return the foreground color a character currently shows."""
    colors = character.animation.current_character_visual.colors
    return colors.fg if colors is not None else None


def background(character: EffectCharacter) -> Color | None:
    """Return the background color a character currently shows."""
    colors = character.animation.current_character_visual.colors
    return colors.bg if colors is not None else None


def rows(body: Body) -> list[str]:
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
    world = make_world()
    with pytest.raises(ValueError, match="shape"):
        world.body().draw()
    with pytest.raises(ValueError, match="Wireframe"):
        world.body(Cube(10)).draw(faces={0: Wireframe()})
    with pytest.raises(ValueError, match="Wireframe"):
        world.body(Cube(10)).draw(Wireframe(), faces={0: Solid()})


def test_wireframe_depth_test_omits_occluded_edges_when_hidden_color_is_none() -> None:
    """The body look forwards its opt-in depth test and suppresses hidden cells."""
    world = make_world(width=81, height=41, perspective=0)
    body = world.body(Torus(20, 8, 36, 18)).draw(Wireframe(hidden_color=None, depth_test=True))
    step(world)
    assert body.mesh is not None
    edges = g3.wireframe(
        body.mesh, world.camera, depth_test=True, bounds=g3.Bounds.for_canvas(terminal_of(world).canvas)
    )
    assert set(body.surface_characters) == {cell for cell, edge in edges.items() if edge.front}


def test_looks_validate_their_settings() -> None:
    """Looks validate their settings."""
    with pytest.raises(ValueError, match="symbol"):
        Shaded(symbols="")
    with pytest.raises(ValueError, match="back"):
        Textured(back="show")  # type: ignore[arg-type]
    for bad in ("界", "ab", "\t"):
        with pytest.raises(ValueError, match="one cell wide"):
            Solid(bad)
    for bad in ("界", "\t"):
        with pytest.raises(ValueError, match="one cell wide"):
            Shaded(symbols=f".{bad}")


def test_draw_defaults_to_shaded_and_fills_the_projected_shape() -> None:
    """With no look, a body is shaded, and a front-on cube fills its projected square."""
    world = make_world()
    body = world.body(Cube(10)).draw()
    assert body.drawn
    assert body.surface_characters == {}  # Nothing is drawn until the world paints.
    step(world)
    cells = body.surface_characters
    columns = {cell.column for cell in cells}
    rows_drawn = {cell.row for cell in cells}
    assert columns == set(range(16, 27))
    assert rows_drawn == set(range(9, 14))
    assert len(cells) == len(columns) * len(rows_drawn)
    assert all(symbol(character) in ".,-~:;=!*#$@" for character in cells.values())


def test_remove_and_clear_hide_surfaces_immediately_and_reuse_pool() -> None:
    """Removal hides owned surface slots immediately; later bodies can reuse the world's pool."""
    world = make_world()
    first = world.body(Cube(8)).draw()
    second = world.body(Cube(8), at=(12, 0, 0)).draw()
    step(world)
    old_cells = list(first.surface_characters.values())
    other_cells = list(second.surface_characters.values())
    assert old_cells
    assert other_cells
    world.remove(first)
    assert not first.surface_characters
    assert not first.drawn
    assert all(not cell.is_visible for cell in old_cells)
    assert all(cell.is_visible for cell in other_cells)
    for body in world.bodies:
        world.remove(body)
    assert not world.bodies
    assert all(not cell.is_visible for cell in world.surface_characters.values())
    third = world.body(Cube(8)).draw()
    step(world)
    assert set(third.surface_characters.values()) == set(old_cells)
    assert all(cell.is_visible for cell in old_cells)


def test_erase_hides_the_cells_at_the_next_step() -> None:
    """Erase hides the body's cells when the world next paints and keeps the pooled characters."""
    world = make_world()
    body = world.body(Cube(10)).draw()
    step(world)
    drawn = list(body.surface_characters.values())
    assert all(character.is_visible for character in drawn)
    body.erase()
    assert not body.drawn
    step(world)
    assert body.surface_characters == {}
    assert not any(character.is_visible for character in drawn)
    assert set(world.surface_characters.values()) >= set(drawn)


def test_pooled_characters_are_reused_and_cells_left_behind_are_hidden() -> None:
    """Pooled characters stay put and are reused, and cells a moving body leaves are hidden."""
    world = make_world()
    body = world.body(Cube(6)).draw()
    step(world)
    first = dict(body.surface_characters)
    body.position = body.position + g3.Vec3(3, 0, 0)
    step(world)
    second = body.surface_characters
    shared = first.keys() & second.keys()
    assert shared
    assert all(first[cell] is second[cell] for cell in shared)
    for cell in first.keys() - second.keys():
        assert not first[cell].is_visible
    for cell, character in second.items():
        assert character.input_coord == cell
        assert character.is_visible
    assert len(world.surface_characters) == len(first.keys() | second.keys())


def test_surface_characters_are_added_characters_not_input_characters() -> None:
    """Surfaces are drawn with characters the world adds, never the effect's input characters."""
    world = make_world()
    body = world.body(Cube(10)).draw()
    step(world)
    added = set(terminal_of(world).get_characters(added_chars=True)) - set(terminal_of(world).get_characters())
    assert set(body.surface_characters.values()) <= added


def test_cells_outside_the_canvas_are_not_drawn() -> None:
    """Cells outside the canvas are not drawn."""
    world = make_world()
    body = world.body(Cube(20), at=(18, 0, 0)).draw()
    step(world)
    canvas = terminal_of(world).canvas
    cells = body.surface_characters
    assert cells
    assert max(cell.column for cell in cells) == canvas.right


def test_an_effect_restyle_lasts_until_the_next_step() -> None:
    """A change the effect makes to a surface character lasts until the world paints it again."""
    world = make_world()
    body = world.body(Cube(10)).draw(Solid("#"))
    step(world)
    character = body.surface_characters[Coord(21, 11)]
    character.animation.set_appearance("X")
    assert symbol(character) == "X"
    step(world)
    assert symbol(character) == "#"


# Looks


def test_shaded_faces_brighten_toward_the_light() -> None:
    """Shaded picks a later symbol and gradient color for a face turned more toward the light."""
    gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=10)
    world = make_world(light="front")
    square = world.body(Cube(6), at=(-10, 0, 0)).draw(Shaded(gradient, symbols="abcd"))
    turned = world.body(Cube(10), at=(8, 0, 0)).rotate("y", 25)
    turned.draw(Shaded(gradient, symbols="abcd"))
    step(world)
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
    world = make_world(light="left")
    body = world.body(Cube(10)).draw(Solid("@", gradient))
    step(world)
    characters = body.surface_characters.values()
    assert {symbol(character) for character in characters} == {"@"}
    assert all(color(character) != Color("#000000") for character in characters)


def test_default_gradient_uses_the_brand_colors() -> None:
    """Looks without a gradient color fully lit faces with the last brand color."""
    world = make_world(light="front")
    body = world.body(Cube(10)).draw(Solid())
    step(world)
    assert color(body.surface_characters[Coord(21, 11)]) == Color("#ffffff")


@pytest.mark.parametrize("row_scale", [1.0, 2.0, 3.0])
def test_textured_row_density_follows_camera(row_scale: float) -> None:
    """Each projected terminal row samples the corresponding texture row for any cell ratio."""
    world = make_world()
    world.camera.row_scale = row_scale
    body = world.body(Box(8, 12, 4)).draw(Textured("AAAA\nBBBB\nCCCC\nDDDD"))
    step(world)
    center = world.camera.center_row
    top = center + 6 / row_scale
    for coord, character in body.surface_characters.items():
        expected_row = int((top - coord.row) + 1e-7) % 4
        assert symbol(character) == "ABCD"[expected_row]


@pytest.mark.parametrize(
    ("look", "expected"),
    [
        (Textured("ABCD\nEFGH", offset=(1, 1)), "G"),
        (Textured("ABCD\nEFGH", offset=(-2, -1)), "H"),
        (Textured("ABCD\nEFGH", scale=2), "A"),
        (Textured("ABCD\nEFGH", offset=(100, 100), repeat=False), " "),
        (Textured("ABCD\nEFGH", offset=(-100, -100), repeat=False), " "),
        (Textured("ABCD\nEFGH", offset=(1, 1), repeat=False), "G"),
    ],
)
def test_texture_controls_sample_text_without_moving_geometry(look: Textured, expected: str) -> None:
    """Offset, scale and repeat transform text sampling while leaving the body pose alone."""
    world = make_world()
    body = world.body(Cube(8)).draw(look)
    fragment = g3.Fragment(1, g3.Z_AXIS, True, 0, 0, (0.125, 1.0))  # noqa: FBT003
    sampled = painter(world)._sample(body, look, fragment)
    assert sampled is not None
    assert sampled[0] == expected
    assert body.position == g3.ORIGIN
    assert body.rotation == g3.Rotation()


@pytest.mark.parametrize("scale", [0, -1, float("inf"), float("nan")])
def test_texture_scale_rejects_invalid_values(scale: float) -> None:
    """Invalid text sizes fail when constructing the look."""
    with pytest.raises(ValueError, match="scale"):
        Textured(scale=scale)


def test_texture_offset_can_be_animated_by_replacing_the_look() -> None:
    """Replacing an immutable look scrolls the text without changing surface coordinates or body pose."""
    world = make_world()
    look = Textured("ABCD")
    body = world.body(Cube(8)).draw(look)
    step(world)
    before = {coord: symbol(character) for coord, character in body.surface_characters.items()}
    body.draw(replace(look, offset=(1, 0)))
    step(world)
    after = {coord: symbol(character) for coord, character in body.surface_characters.items()}
    assert after.keys() == before.keys()
    assert all(after[coord] == "BCDA"["ABCD".index(value)] for coord, value in before.items())
    assert body.rotation == g3.Rotation()


def test_textured_cube_shows_the_input_text_on_its_front_face() -> None:
    """A front-on textured cube shows the input text from the face's top left corner."""
    world = make_world()
    body = world.body(Box(10, 6, 10)).draw(Textured())
    step(world)
    assert rows(body) == ["Hello TTE H", "surfaces! s", "01234567890"]
    assert painter(world).input_text == TEXT


def test_textured_text_can_be_any_string_and_repeats() -> None:
    """A textured look can wrap any string, and repeats it across a larger face."""
    world = make_world()
    body = world.body(Box(10, 4, 10)).draw(Textured("ab\ncd"))
    step(world)
    assert rows(body) == ["abababababa", "cdcdcdcdcdc", "abababababa"]


def test_textured_faces_without_a_layout_are_shaded_in_the_back_color() -> None:
    """Faces with no texture layout, such as a cylinder's cap, are shaded in the back color."""
    world = make_world()
    back = Color("#123456")
    body = world.body(Cylinder(8, 6)).rotate("x", 90).draw(Textured(back_color=back))
    step(world)
    characters = list(body.surface_characters.values())
    assert characters
    assert all(color(character) == back for character in characters)
    assert all(symbol(character) in ".,-~:;=!*#$@" for character in characters)


def test_textured_dim_shows_the_far_side_through_gaps() -> None:
    """With `back="dim"`, spaces in the text show the far side in the back color."""
    world = make_world()
    back = Color("#123456")
    hide = world.body(Cylinder(8, 6), at=(-10, 0, 0)).draw(Textured("a b c d e f g h"))
    dim = world.body(Cylinder(8, 6), at=(10, 0, 0)).draw(Textured("a b c d e f g h", back="dim", back_color=back))
    step(world)
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
    assert Box(10, 6, 8).texture_cell(fragment) == (5.0, 0.0)
    assert Box(10, 6, 8).texture_cell(fragment._replace(tag=1)) == (4.0, 0.0)
    assert Cube(10).texture_cell(fragment) == (5.0, 0.0)
    for shape in (Prism(), Pyramid(), Cylinder(), Sphere()):
        place = shape.texture_cell(fragment)
        assert place is not None
        assert place[1] == (-shape.radius * math.pi / 4 if isinstance(shape, Sphere) else 0.0)
        assert shape.texture_cell(no_uv) is None
    assert Torus().texture_cell(fragment) is None
    assert Tetrahedron().texture_cell(fragment) is None
    bottom = Cylinder(10, 8).texture_cell(fragment._replace(uv=(0.0, 0.0)))
    assert bottom == pytest.approx((2 * 3.141592653589793 * 10 / 4, 8 / g3.TERMINAL_ROW_SCALE))


def test_a_sphere_measures_its_texture_from_the_middle_of_the_front() -> None:
    """A sphere's texture cell is zero at the middle of the front on the equator, and wraps behind the sphere."""
    sphere = Sphere(10)
    around = 2 * math.pi * 10
    middle = g3.Fragment(1.0, g3.Z_AXIS, True, 0, 0, (0.0, 0.5))  # noqa: FBT003
    assert sphere.texture_cell(middle) == pytest.approx((0.0, 0.0))
    assert sphere.texture_cell(middle._replace(uv=(0.25, 0.5))) == pytest.approx((around / 4, 0.0))
    assert sphere.texture_cell(middle._replace(uv=(0.75, 0.5))) == pytest.approx((-around / 4, 0.0))


def test_textured_sphere_centers_the_text_where_layout_text_does() -> None:
    """Text on a sphere sits where `surface.layout_text` puts it: the same rows, and nearly all the same columns."""
    text = "\n".join("".join(chr(0x1E00 + row * 41 + column) for column in range(41)) for row in range(5))
    laid_out = make_world(text, width=121, height=61)
    characters = terminal_of(laid_out).get_characters()
    sphere = Sphere.fit_text(characters)
    laid_out.body(sphere).surface.layout_text(characters)
    for character in characters:
        terminal_of(laid_out).set_character_visibility(character, is_visible=True)
    step(laid_out)
    textured = make_world(text, width=121, height=61)
    body = textured.body(Sphere(sphere.radius)).draw(Textured())
    step(textured)

    def position(symbol_: str) -> tuple[int, int]:
        row, column = divmod(ord(symbol_) - 0x1E00, 41)
        return column, row

    placed = {
        character.motion.current_coord: position(character.input_symbol)
        for character in characters
        if character.view.facing_amount > 0.5
    }
    sampled = {coord: position(symbol(cell)) for coord, cell in body.surface_characters.items()}
    shared = placed.keys() & sampled.keys()
    assert len(shared) > 50
    assert all(placed[coord][1] == sampled[coord][1] for coord in shared)
    assert sum(placed[coord] == sampled[coord] for coord in shared) > 0.8 * len(shared)


def test_wireframe_draws_edges_with_hidden_edges_dimmed_or_left_out() -> None:
    """Wireframe draws edge symbols, with hidden edges in the hidden color or left out."""
    front, hidden = Color("#00ff00"), Color("#ff0000")
    world = make_world()
    shown = world.body(Cube(10), at=(-10, 0, 0)).rotate("y", 30).rotate("x", 20)
    shown.draw(Wireframe(front, hidden))
    left_out = world.body(Cube(10), at=(10, 0, 0)).rotate("y", 30).rotate("x", 20)
    left_out.draw(Wireframe(front, None))
    step(world)
    shown_colors = {color(character) for character in shown.surface_characters.values()}
    assert shown_colors == {front, hidden}
    assert {color(character) for character in left_out.surface_characters.values()} == {front}
    assert {symbol(character) for character in shown.surface_characters.values()} <= set("-/|\\")


def test_per_face_looks_draw_only_their_faces() -> None:
    """Looks given per face draw those faces, and others are left out without a body look."""
    world = make_world()
    body = world.body(Cube(10)).rotate("y", 30).draw(faces={0: Solid("A")})
    step(world)
    assert {symbol(character) for character in body.surface_characters.values()} == {"A"}
    body.draw(Solid("B"), faces={0: Solid("A")})
    step(world)
    assert {symbol(character) for character in body.surface_characters.values()} == {"A", "B"}


def test_per_face_looks_take_surface_face_names() -> None:
    """Face names from the surface pick the same faces as their mesh tags."""
    for shape in (Cube(10), Box(12, 8, 6), Prism(5), Pyramid(5), Cylinder()):
        world = make_world()
        body = world.body(shape)
        tags = shape.face_tags()
        assert tuple(tags) == body.surface.faces
        assert body.mesh is not None
        mesh_tags = {face.tag for face in body.mesh.faces}
        assert set(tags.values()) == mesh_tags
        body.draw(faces={name: Solid("A") for name in tags})
        assert body._face_looks.keys() == mesh_tags


def test_face_names_match_the_faces_characters_sit_on() -> None:
    """Each mesh face's center lies on the surface face of the name that maps to its tag."""
    for shape in (Cube(10), Box(12, 8, 6), Prism(5), Prism(3), Pyramid(4), Pyramid(5), Cylinder()):
        mesh, surface = shape.build_mesh(), shape.build_surface()
        names = {tag: name for name, tag in shape.face_tags().items()}
        for face in mesh.faces:
            corners = [mesh.vertices[index] for index in face.indices]
            center = g3.Vec3(
                sum(p.x for p in corners) / len(corners),
                sum(p.y for p in corners) / len(corners),
                sum(p.z for p in corners) / len(corners),
            )
            position = surface.locate(center)
            assert surface._face_at((position.x, position.y, position.z)) == names[face.tag]


def test_a_named_face_draws_that_face() -> None:
    """A cube turned to show its front and right draws only the front for `"front"`, and the same for tag 0."""
    world = make_world()
    named = world.body(Cube(10), at=(-10, 0, 0)).rotate("y", 30).draw(faces={"front": Solid("A")})
    tagged = world.body(Cube(10), at=(10, 0, 0)).rotate("y", 30).draw(faces={0: Solid("A")})
    step(world)
    assert named.surface_characters
    assert len(named.surface_characters) == len(tagged.surface_characters)


def test_per_face_looks_reject_unknown_and_repeated_faces() -> None:
    """An unknown face name or tag raises, and so does naming one face twice."""
    world = make_world()
    with pytest.raises(ValueError, match="no face 'lid'"):
        world.body(Cube(10)).draw(faces={"lid": Solid()})
    with pytest.raises(ValueError, match="no face 6"):
        world.body(Cube(10)).draw(faces={6: Solid()})
    with pytest.raises(ValueError, match="same face"):
        world.body(Cube(10)).draw(faces={"front": Solid(), 0: Shaded()})
    with pytest.raises(ValueError, match="no face 'front'"):
        world.body(Sphere(10)).draw(faces={"front": Solid()})
    assert world.body(Prism(5)).draw(faces={5: Solid()}).drawn  # A prism's top by mesh tag.
    assert world.body(Tetrahedron(10)).draw(faces={0: Solid()}).drawn


# Depth and layers


def test_bodies_share_one_depth_buffer() -> None:
    """Where bodies overlap, the nearer one is drawn and the farther one shows only around it."""
    world = make_world()
    far = world.body(Cube(12), at=(0, 0, -20)).draw(Solid("F"))
    near = world.body(Cube(6), at=(0, 0, 10)).draw(Solid("N"))
    step(world)
    assert Coord(21, 11) in near.surface_characters
    assert Coord(21, 11) not in far.surface_characters
    assert far.surface_characters
    assert not far.surface_characters.keys() & near.surface_characters.keys()


def painter_order(character: EffectCharacter) -> tuple[int, float]:
    """Return what the terminal orders characters by within a cell, ahead of creation order."""
    return character.layer, character._depth_order


def test_surface_cells_order_by_depth_just_below_text_on_them() -> None:
    """Drawn cells sit on layer 0, ordered by depth, just below a character on the same spot of the body."""
    world = make_world()
    body = world.body(Box(10, 6, 10)).draw()
    character = attach(world, body, (0, 0, 5))
    step(world)
    cell = body.surface_characters[character.motion.current_coord]
    assert painter_order(cell) < painter_order(character)
    assert cell.layer == character.layer == 0
    order = body.surface_characters[Coord(21, 11)]._depth_order
    body.position = (0, 0, 10)
    step(world)
    assert body.surface_characters[Coord(21, 11)]._depth_order > order


def test_surface_slightly_nearer_than_free_text_draws_over_it() -> None:
    """A surface cell a fraction of a column nearer than a character not on that body is drawn over it."""
    world = make_world()
    body = world.body(Box(10, 6, 10)).draw()
    character = attach(world, world.body(), (0, 0, 4.7))
    step(world)
    cell = body.surface_characters[character.motion.current_coord]
    assert painter_order(cell) > painter_order(character)


def test_text_on_a_drawn_body_reads_over_its_surface_in_the_frame() -> None:
    """A character on a drawn body shows over the surface cell it sits on in the rendered frame."""
    world = make_world("Z")
    body = world.body(Box(10, 6, 10)).draw(Solid("#"))
    attach(world, body, (0, 0, 5))
    step(world)
    frame = terminal_of(world).get_formatted_output_string()
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
def test_text_on_a_turned_face_reads_over_it(
    perspective: float, axis: str, angle: float, offset: tuple[float, float, float]
) -> None:
    """Text on a slanted front face shows over that face, though the face is measured at the cell center."""
    world = make_world("Z", perspective=perspective)
    body = world.body(Cube(12), at=offset).rotate(axis, angle).draw(Solid("#"))
    character = attach(world, body, (2, 0, 6))
    step(world)
    cell = body.surface_characters[character.motion.current_coord]
    assert painter_order(cell) < painter_order(character)
    assert "Z" in terminal_of(world).get_formatted_output_string()


@pytest.mark.parametrize("perspective", [0, 1, 0.0001])
def test_a_nearer_surface_covers_text_on_a_turned_face(perspective: float) -> None:
    """A surface a fraction of a column in front of a slanted face still covers the text on that face."""
    world = make_world("Z", perspective=perspective)
    body = world.body(Cube(12)).rotate("y", 15)
    character = attach(world, body, (2, 0, 6))
    step(world)
    cell = character.motion.current_coord
    shield = world.body(Box(4, 4, 2)).draw(Solid("#"))
    # Turned like the face and moved so its front sits 0.2 columns in front of the character, along the normal.
    shield.rotate("y", 15)
    normal = body.rotation.apply(g3.Z_AXIS)
    shield.position = character.world_position + normal * (0.2 - 1.0)
    step(world)
    assert painter_order(shield.surface_characters[cell]) > painter_order(character)


@pytest.mark.parametrize("perspective", [0, 1])
@pytest.mark.parametrize("shape", [Sphere(12, segments=24), Cylinder(12, 12, 24)])
def test_text_on_a_curved_body_reads_over_its_facets(perspective: float, shape: Shape) -> None:
    """Text on the true curved surface sits just outside the drawn facets, so text facing the viewer reads on top."""
    world = make_world("\n".join(["ABCDEFGHIJKLMNOPQRSTUVWXYZ"] * 4), width=61, height=31, perspective=perspective)
    terminal = terminal_of(world)
    characters = [character for character in terminal.get_characters() if character.input_symbol != " "]
    body = world.body(shape).rotate("y", 30).draw(Solid("#"))
    body.surface.layout_text(characters)
    for character in characters:
        terminal.set_character_visibility(character, is_visible=True)
    step(world)
    checked = 0
    for character in characters:
        cell = body.surface_characters.get(character.motion.current_coord)
        # Edge-on text at the rim can sit over a neighboring facet that really is nearer.
        if cell is not None and character.view.facing_amount > 0.2:
            assert painter_order(cell) < painter_order(character)
            checked += 1
    assert checked > 20


@pytest.mark.parametrize("perspective", [0, 1])
def test_text_inside_a_torus_stays_behind_its_near_side(perspective: float) -> None:
    """Text on the inner wall of a torus's far side, facing the viewer, is still covered by the tube in front of it."""
    world = make_world("Z", perspective=perspective)
    body = world.body(Torus(12, 4)).draw(Solid("#"))
    character = attach(world, body, (0, 0, -8))
    step(world)
    cell = body.surface_characters[character.motion.current_coord]
    assert painter_order(cell) > painter_order(character)


def test_text_on_a_far_face_stays_behind_the_near_face() -> None:
    """Text on a body's back face does not show through the front face covering it."""
    world = make_world("Z")
    body = world.body(Cube(12)).rotate("y", 15).draw(Solid("#"))
    character = attach(world, body, (1, 0, -6))
    step(world)
    cell = body.surface_characters[character.motion.current_coord]
    assert painter_order(cell) > painter_order(character)


def test_unchanged_cells_keep_their_visual() -> None:
    """Cells whose symbol and color don't change keep the same visual between steps."""
    world = make_world()
    body = world.body(Cube(10)).draw(Solid())
    step(world)
    visuals = {
        cell: character.animation.current_character_visual for cell, character in body.surface_characters.items()
    }
    step(world)
    for cell, character in body.surface_characters.items():
        assert character.animation.current_character_visual is visuals[cell]
    pair = painter(world).pair(Color("#abcdef"))
    assert pair == ColorPair(fg=Color("#abcdef"))
    assert painter(world).pair(Color("#abcdef")) is pair


def test_a_far_body_shows_behind_the_far_side_seen_through_text_gaps() -> None:
    """Through a gap in dim text, the body's own far side is nearer than a body behind it, so it wins."""
    world = make_world()
    back = Color("#123456")
    hollow = world.body(Cylinder(8, 8)).draw(Textured(" ", back="dim", back_color=back))
    behind = world.body(Cube(6), at=(0, 0, -40)).draw(Solid("#"))
    step(world)
    center = hollow.surface_characters[Coord(21, 11)]
    assert color(center) == back
    assert Coord(21, 11) not in behind.surface_characters


def test_textured_text_keeps_every_drawn_symbol_one_cell_wide() -> None:
    """Wide characters become two blank cells and symbols that can't be drawn alone become one."""
    world = make_world()
    body = world.body(Box(10, 2, 10)).draw(Textured("a界b\tc"))
    step(world)
    assert rows(body)[0].startswith("a  b c")
    assert drawing._text_grid("a界b\tc") == (["a  b c"], 6)


def test_input_text_counts_a_wide_character_once() -> None:
    """The default text keeps input columns: a wide character's second column adds no extra gap."""
    world = make_world("a界b\nxyz")
    assert painter(world).input_text == "a界b\nxyz"
    assert drawing._text_grid(painter(world).input_text)[0] == ["a  b", "xyz"]


def test_input_text_keeps_blank_lines() -> None:
    """A blank line inside the input stays in the default text, so later rows keep their place."""
    world = make_world("a\n\nb")
    assert painter(world).input_text == "a\n\nb"


def test_solid_background_fills_cells_with_the_lit_color() -> None:
    """`Solid(background=True)` paints the lit color behind a space instead of drawing its symbol."""
    world = make_world()
    stone = Gradient(Color("#202020"), Color("#e0e0e0"), steps=8)
    plain = world.body(Cube(8), at=(-10, 0, 0)).rotate("y", 30).rotate("x", 20).draw(Solid(gradient=stone))
    filled = (
        world.body(Cube(8), at=(10, 0, 0)).rotate("y", 30).rotate("x", 20).draw(Solid(gradient=stone, background=True))
    )
    step(world)
    plain_colors = sorted(str(color(character)) for character in plain.surface_characters.values())
    filled_cells = list(filled.surface_characters.values())
    assert filled_cells
    assert all(symbol(character) == " " and color(character) is None for character in filled_cells)
    assert sorted(str(background(character)) for character in filled_cells) == plain_colors
    assert len({background(character) for character in filled_cells}) > 1  # Faces are lit differently.


def test_textured_background_fills_every_cell_under_the_text() -> None:
    """A textured look with a background fills text cells, blanks and untextured faces alike."""
    world = make_world()
    fill = Color("#334455")
    box = world.body(Box(10, 6, 10)).draw(Textured("ab \ncd ", background=fill, repeat=False))
    cap = world.body(Cylinder(8, 6), at=(15, 0, 0)).rotate("x", 90).draw(Textured(background=fill))
    step(world)
    for character in [*box.surface_characters.values(), *cap.surface_characters.values()]:
        assert background(character) == fill
    assert {symbol(character) for character in cap.surface_characters.values()} == {" "}
    assert set("abcd") <= {symbol(character) for character in box.surface_characters.values()}


def test_textured_gradient_background_is_lit() -> None:
    """A gradient background runs from unlit to fully lit, as `Solid` colors do."""
    world = make_world()
    stone = Gradient(Color("#202020"), Color("#e0e0e0"), steps=8)
    body = world.body(Cube(8)).rotate("y", 30).rotate("x", 20).draw(Textured("x", background=stone))
    step(world)
    fills = {background(character) for character in body.surface_characters.values()}
    assert len(fills) > 1
    assert fills <= set(stone)


def test_textured_ink_defaults_to_the_brand_gradient_following_the_light() -> None:
    """The default ink is the brand gradient picked by the light, so text with no ink settings looks as before."""
    world = make_world()
    body = world.body(Box(10, 6, 10)).draw(Textured())
    step(world)
    expected = drawing._gradient(None).get_color_at_fraction(
        drawing._AMBIENT + (1 - drawing._AMBIENT) * g3.lambert(g3.Z_AXIS, world.world_light)
    )
    assert {color(character) for character in body.surface_characters.values()} == {expected}


@pytest.mark.parametrize(("amount", "expected"), [(0.0, "ffffff"), (1.0, None)])
def test_ink_light_sets_how_much_shadow_darkens_text(amount: float, expected: str | None) -> None:
    """`light=0` keeps the ink color everywhere, and `light=1` darkens it as much as the face's shadow."""
    world = make_world(light="right")
    body = world.body(Box(10, 6, 10)).draw(Textured("x", ink=Ink(Color("#ffffff"), light=amount)))
    step(world)
    colors = {color(character) for character in body.surface_characters.values()}
    assert len(colors) == 1
    shown = colors.pop()
    assert shown is not None
    if expected is not None:
        assert shown.rgb_color == expected
    else:
        assert shown.rgb_ints[0] < 255  # The front faces away from a light on the right.


def test_ink_spread_across_the_text_keeps_colors_on_their_letters() -> None:
    """A gradient spread across the text gives each column its own color, whatever the light."""
    world = make_world()
    red, blue = Color("#ff0000"), Color("#0000ff")
    ink = Ink(Gradient(red, blue, steps=10), spread=Gradient.Direction.HORIZONTAL, light=0)
    body = world.body(Box(10, 6, 10)).draw(Textured("abcdefghij", ink=ink, repeat=False))
    step(world)
    by_symbol = {symbol(character): color(character) for character in body.surface_characters.values()}
    assert by_symbol["a"] == red
    assert by_symbol["j"] == blue


def test_ink_and_background_validation() -> None:
    """Ink rejects unknown spreads and light outside 0 to 1, and `back="dim"` can't be combined with a fill."""
    with pytest.raises(ValueError, match="spread"):
        Ink(spread="text")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="light"):
        Ink(light=1.5)
    with pytest.raises(ValueError, match="dim"):
        Textured(back="dim", background=Color("#000000"))


def test_painter_shares_pairs_with_backgrounds_and_shades_by_light_level() -> None:
    """Pairs with a background are shared, and shading rounds the light so nearby levels reuse one color."""
    world = make_world()
    fg, bg = Color("#abcdef"), Color("#123456")
    pair = painter(world).pair(fg, bg)
    assert pair == ColorPair(fg=fg, bg=bg)
    assert painter(world).pair(fg, bg) is pair
    assert painter(world).pair(fg) is not pair
    white = Color("#ffffff")
    assert painter(world).shade(white, 0.0, 0.2) is white
    assert painter(world).shade(white, 1.0, 0.5) is painter(world).shade(white, 1.0, 0.51)
    assert painter(world).shade(white, 1.0, 1.0) == white


def test_text_on_a_filled_body_draws_over_the_fill() -> None:
    """A character on a background-filled body shows its symbol and color over the fill, in front of itself."""
    world = make_world("Z")
    fill = Color("#334455")
    body = world.body(Box(10, 6, 10)).draw(Solid(gradient=Gradient(fill, fill), background=True))
    character = attach(world, body, (0, 0, 5))
    character.animation.set_appearance("Z", ColorPair(fg="ff0000"))
    step(world)
    cell = body.surface_characters[character.motion.current_coord]
    assert symbol(cell) == "Z"
    assert color(cell) == Color("ff0000")
    assert background(cell) == fill
    assert painter_order(cell) > painter_order(character)
    character.animation.set_appearance("Y", ColorPair(fg="00ff00"))
    step(world)
    assert (symbol(cell), color(cell), background(cell)) == ("Y", Color("00ff00"), fill)


def test_the_fill_returns_when_text_leaves_the_surface() -> None:
    """Once the character detaches, the cell it sat on shows only the fill again."""
    world = make_world("Z")
    body = world.body(Box(10, 6, 10)).draw(Solid(background=True))
    character = attach(world, body, (0, 0, 5))
    step(world)
    coord = character.motion.current_coord
    character.detach()
    step(world)
    cell = body.surface_characters[coord]
    assert symbol(cell) == " "
    assert color(cell) is None
    assert background(cell) is not None
    assert cell.layer == 0


def test_text_keeps_its_own_background_and_layer_over_a_fill() -> None:
    """A character's own background wins over the fill, and the cell takes the character's layer."""
    world = make_world("Z")
    body = world.body(Box(10, 6, 10)).draw(Solid(background=True))
    character = attach(world, body, (0, 0, 5))
    character.layer = 2
    character.animation.set_appearance("Z", ColorPair(fg="ff0000", bg="0000ff"))
    step(world)
    cell = body.surface_characters[character.motion.current_coord]
    assert background(cell) == Color("0000ff")
    assert cell.layer == 2
    assert painter_order(cell) > painter_order(character)


def test_text_replaces_cells_without_a_fill() -> None:
    """Without a background fill, a character still draws over the cell, which keeps its own symbol."""
    world = make_world("Z")
    body = world.body(Box(10, 6, 10)).draw(Solid("#"))
    character = attach(world, body, (0, 0, 5))
    step(world)
    cell = body.surface_characters[character.motion.current_coord]
    assert symbol(cell) == "#"
    assert painter_order(cell) < painter_order(character)


@pytest.mark.parametrize(
    ("ink", "expected"),
    [
        (None, "ff0000"),
        (Ink(light=0), "ff0000"),
        (Ink(Color("#00ff00"), light=0), "00ff00"),
        (Ink(Gradient(Color("#00ff00"), Color("#0000ff")), light=0), "0000ff"),
    ],
)
def test_solid_ink_colors_text_over_the_fill(ink: Ink | None, expected: str) -> None:
    """`Solid.ink` keeps, darkens or replaces the color of characters drawn over its fill."""
    world = make_world("Z", light="front")
    body = world.body(Box(10, 6, 10)).draw(Solid(background=True, ink=ink))
    character = attach(world, body, (0, 0, 5))
    character.animation.set_appearance("Z", ColorPair(fg="ff0000"))
    step(world)
    cell = body.surface_characters[character.motion.current_coord]
    shown = color(cell)
    assert shown is not None
    if ink is not None and isinstance(ink.color, Gradient):
        assert shown in set(ink.color)  # Follows the light: fully lit from the front.
    else:
        assert shown.rgb_color == expected


def test_solid_ink_light_darkens_text_in_shadow() -> None:
    """`Ink(light=1)` darkens a character's own color on a face turned from the light."""
    world = make_world("Z", light="right")
    body = world.body(Box(10, 6, 10)).draw(Solid(background=True, ink=Ink(light=1)))
    character = attach(world, body, (0, 0, 5))
    character.animation.set_appearance("Z", ColorPair(fg="ffffff"))
    step(world)
    shown = color(body.surface_characters[character.motion.current_coord])
    assert shown is not None
    assert shown.rgb_ints[0] < 255


def test_solid_ink_spread_runs_across_the_input_text() -> None:
    """A spread ink colors each character by its input position across the input text."""
    world = make_world("AB")
    red, blue = Color("#ff0000"), Color("#0000ff")
    ink = Ink(Gradient(red, blue, steps=4), spread=Gradient.Direction.HORIZONTAL, light=0)
    body = world.body(Box(20, 6, 10)).draw(Solid(background=True, ink=ink))
    first, second = terminal_of(world).get_characters()
    for character, x in ((first, -2), (second, 2)):
        terminal_of(world).set_character_visibility(character, is_visible=True)
        character.attach(body, at=body.surface.locate((x, 0, 5)))
    step(world)
    assert color(body.surface_characters[first.motion.current_coord]) == red
    assert color(body.surface_characters[second.motion.current_coord]) == blue


def test_text_a_rounding_error_off_the_surface_still_draws_over_the_fill() -> None:
    """A character landing on a surface can keep a trace of height, and still counts as on it."""
    world = make_world("Z")
    body = world.body(Box(10, 6, 10)).draw(Solid(background=True))
    character = attach(world, body, (0, 0, 5))
    position = character.motion._xyz
    character.motion._xyz = (position[0], position[1], 1e-15)
    step(world)
    assert symbol(body.surface_characters[character.motion.current_coord]) == "Z"


def test_text_keeps_its_modes_over_a_fill() -> None:
    """Bold, underline and other modes of a character's visual carry over to the cell drawn over the fill."""
    world = make_world("Z")
    body = world.body(Box(10, 6, 10)).draw(Solid(background=True))
    character = attach(world, body, (0, 0, 5))
    animation = character.animation
    animation.current_character_visual = replace(animation.current_character_visual, bold=True, underline=True)
    step(world)
    shown = body.surface_characters[character.motion.current_coord].animation.current_character_visual
    assert shown.bold
    assert shown.underline
    assert shown.colors is not None
    assert shown.colors.bg is not None
    animation.current_character_visual = replace(animation.current_character_visual, underline=False)
    step(world)
    shown = body.surface_characters[character.motion.current_coord].animation.current_character_visual
    assert shown.bold
    assert not shown.underline


def test_text_sharing_a_cell_over_a_fill_shows_the_one_painted_last() -> None:
    """Two characters on the same spot show the one the terminal paints last, the higher character ID on a tie."""
    world = make_world("AB")
    body = world.body(Box(10, 6, 10)).draw(Solid(background=True))
    first, second = terminal_of(world).get_characters()
    for character in (first, second):  # The first attached is met first, but B paints last.
        terminal_of(world).set_character_visibility(character, is_visible=True)
        character.attach(body, at=body.surface.locate((0, 0, 5)))
    step(world)
    assert symbol(body.surface_characters[first.motion.current_coord]) == "B"


def test_a_new_spread_ink_never_reuses_an_old_inks_colors() -> None:
    """Replacing a body's look with a new spread ink shows the new gradient, even if the old ink is gone."""
    world = make_world("A")
    body = world.body(Box(10, 6, 10))
    character = attach(world, body, (0, 0, 5))
    for code in ("#ff0000", "#00ff00", "#0000ff") * 30:
        gradient = Gradient(Color(code), Color(code))
        body.draw(Solid(background=True, ink=Ink(gradient, spread=Gradient.Direction.HORIZONTAL, light=0)))
        step(world)
        assert color(body.surface_characters[character.motion.current_coord]) == Color(code)
