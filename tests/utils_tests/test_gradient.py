import pytest

from terminaltexteffects.engine.motion import Coord
from terminaltexteffects.utils.graphics import Color, Gradient, random_color

pytestmark = [pytest.mark.utils, pytest.mark.smoke]


def test_random_color() -> None:
    assert isinstance(random_color(), Color)


def test_gradient_zero_stops() -> None:
    with pytest.raises(ValueError):
        Gradient()


def test_gradient_zero_steps() -> None:
    with pytest.raises(ValueError):
        Gradient(Color("ffffff"), steps=0)


def test_gradient_zero_steps_tuple() -> None:
    with pytest.raises(ValueError):
        Gradient(Color("ffffff"), Color("000000"), Color("ff0000"), steps=(1, 0))


def test_gradient_slice() -> None:
    g = Gradient(Color("ffffff"), Color("000000"), steps=4)
    assert g[0] == Color("ffffff")
    assert g[-1] == Color("000000")
    assert g[1:3] == [Color("bfbfbf"), Color("7f7f7f")]


def test_gradient_iter() -> None:
    g = Gradient(Color("ffffff"), Color("000000"), steps=4)
    for color in g:
        assert isinstance(color, Color)


def test_gradient_str() -> None:
    g = Gradient(Color("ffffff"), Color("000000"), steps=4)
    assert "Stops(ffffff, 000000)" in str(g)


def test_gradient_len() -> None:
    g = Gradient(Color("ffffff"), Color("000000"), steps=4)
    assert len(g) == 5


def test_gradient_length_single_color() -> None:
    g = Gradient(Color("ffffff"), steps=5)
    assert len(g.spectrum) == 5


def test_gradient_length_two_colors() -> None:
    g = Gradient(Color("000000"), Color("ffffff"), steps=5)
    assert len(g.spectrum) == 6


def test_gradient_length_three_colors() -> None:
    g = Gradient(Color("000000"), Color("ffffff"), Color("000000"), steps=5)
    assert len(g.spectrum) == 11


def test_gradient_length_same_color_multiple_times() -> None:
    g = Gradient(Color("ffffff"), Color("ffffff"), Color("ffffff"), Color("ffffff"), steps=4)
    assert len(g.spectrum) == 13


def test_gradient_length_same_color_multiple_times_with_tuple_steps() -> None:
    g = Gradient(Color("ffffff"), Color("ffffff"), Color("ffffff"), Color("ffffff"), steps=(4, 6))
    assert len(g.spectrum) == 17


def test_gradient_single_color() -> None:
    g = Gradient(Color("ffffff"), steps=5)
    assert all(color == Color("ffffff") for color in g.spectrum)


def test_gradient_two_colors() -> None:
    g = Gradient(Color("000000"), Color("ffffff"), steps=3)
    assert g.spectrum[0] == Color("000000") and g.spectrum[-1] == Color("ffffff")


def test_gradient_single_step() -> None:
    g = Gradient(Color("ffffff"), steps=1)
    assert g.spectrum[0] == Color("ffffff")


def test_gradient_three_colors() -> None:
    g = Gradient(Color("ffffff"), Color("000000"), Color("ffffff"), steps=4)
    assert g.spectrum[0] == Color("ffffff") and g.spectrum[4] == Color("000000") and g.spectrum[-1] == Color("ffffff")


def test_gradient_loop() -> None:
    g = Gradient(Color("ffffff"), Color("000000"), steps=4, loop=True)
    assert g.spectrum[-1] == Color("ffffff")


def test_gradient_get_color_at_fraction() -> None:
    g = Gradient(Color("ffffff"), Color("000000"), steps=4)
    assert g.get_color_at_fraction(0) == Color("ffffff")
    assert g.get_color_at_fraction(0.5) == Color("7f7f7f")
    assert g.get_color_at_fraction(1) == Color("000000")


def test_gradient_get_color_at_fraction_invalid_float() -> None:
    g = Gradient(Color("ffffff"), Color("000000"), steps=4)
    with pytest.raises(ValueError):
        g.get_color_at_fraction(1.1)


@pytest.mark.parametrize(
    "direction",
    [
        Gradient.Direction.DIAGONAL,
        Gradient.Direction.HORIZONTAL,
        Gradient.Direction.VERTICAL,
        Gradient.Direction.RADIAL,
    ],
)
def test_gradient_build_coordinate_color_mapping(direction) -> None:
    g = Gradient(Color("ffffff"), Color("000000"), steps=4)
    coordinate_map = g.build_coordinate_color_mapping(10, 10, direction)
    if direction == Gradient.Direction.DIAGONAL:
        assert coordinate_map[Coord(1, 0)] == Color("ffffff")
        assert coordinate_map[Coord(10, 10)] == Color("000000")
    elif direction == Gradient.Direction.HORIZONTAL:
        assert coordinate_map[Coord(1, 0)] == Color("ffffff")
        assert coordinate_map[Coord(10, 0)] == Color("000000")
    elif direction == Gradient.Direction.VERTICAL:
        assert coordinate_map[Coord(1, 1)] == Color("ffffff")
        assert coordinate_map[Coord(1, 10)] == Color("000000")
    elif direction == Gradient.Direction.RADIAL:
        assert coordinate_map[Coord(5, 5)] == Color("ffffff")
        assert coordinate_map[Coord(10, 10)] == Color("000000")


def test_gradient_build_coordinate_color_mapping_invalid_row_column() -> None:
    g = Gradient(Color("ffffff"), Color("000000"), steps=4)
    with pytest.raises(ValueError):
        g.build_coordinate_color_mapping(0, 10, Gradient.Direction.HORIZONTAL)
    with pytest.raises(ValueError):
        g.build_coordinate_color_mapping(10, 0, Gradient.Direction.HORIZONTAL)


def test_color_invalid_xterm_color() -> None:
    with pytest.raises(ValueError):
        Color(256)


def test_color_invalid_hex_color() -> None:
    with pytest.raises(ValueError):
        Color("ffffzz")


def test_color_valid_hex_with_hash():
    assert Color("#ffffff") == Color("ffffff")


def test_color_hex_rgb_ints():
    assert Color("000000").rgb_ints == (0, 0, 0)


def test_color_xterm_rgb_ints():
    assert Color(0).rgb_ints == (0, 0, 0)


def test_color_not_equal():
    assert Color("ffffff") != Color("000000")


def test_color_not_equal_different_types():
    assert Color("ffffff") != 0
    assert not Color(0) == "ffffff"


def test_color_is_hashable():
    hash(Color("ffffff"))
    hash(Color(0))


def test_color_is_iterable():
    assert list(Color("ffffff")) == [Color("ffffff")]


def test_color_repr():
    assert repr(Color("ffffff")) == "Color('ffffff')"


def test_color_str():
    assert "Color Code: ffffff" in str(Color("ffffff"))
