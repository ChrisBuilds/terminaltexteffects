"""Tests for color, color-pair, and gradient utilities."""

from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import FrozenInstanceError, asdict, fields
from typing import cast

import pytest

from terminaltexteffects.engine.motion import Coord
from terminaltexteffects.utils.graphics import Color, ColorPair, Gradient, random_color, shift_color_towards

# Test names provide the documentation for straightforward single-assertion cases.
# ruff: noqa: D103

pytestmark = [pytest.mark.utils, pytest.mark.smoke]


def test_random_color() -> None:
    assert isinstance(random_color(), Color)


def test_color_pair_init() -> None:
    cp = ColorPair("#ffffff", "#000000")
    assert cp.fg == Color("#ffffff")
    assert cp.bg == Color("#000000")


def test_color_pair_init_single_color() -> None:
    cp = ColorPair("#ffffff")
    assert cp.fg == Color("#ffffff")
    assert cp.bg is None


def test_color_pair_canonical_fields() -> None:
    color_pair = ColorPair(fg="#ffffff", bg=0)

    assert color_pair.fg == Color("#ffffff")
    assert color_pair.bg == Color(0)
    assert tuple(field.name for field in fields(color_pair)) == ("fg", "bg")
    assert set(asdict(color_pair)) == {"fg", "bg"}


def test_color_pair_has_no_legacy_field_aliases() -> None:
    color_pair = ColorPair(fg="#ffffff", bg=0)

    assert not hasattr(color_pair, "fg_color")
    assert not hasattr(color_pair, "bg_color")


def test_color_pair_declares_canonical_positional_match_fields() -> None:
    """Expose canonical field order to pattern matching on supported Python versions."""
    assert ColorPair.__match_args__ == ("fg", "bg")


@pytest.mark.parametrize("attribute", ["fg", "bg"])
def test_color_pair_is_immutable(attribute: str) -> None:
    color_pair = ColorPair(fg="#ffffff", bg=0)

    with pytest.raises(FrozenInstanceError):
        setattr(color_pair, attribute, None)


def test_color_pair_supports_deepcopy() -> None:
    color_pair = ColorPair(fg="#ffffff", bg=0)

    copied_pair = deepcopy(color_pair)

    assert copied_pair == color_pair
    assert copied_pair is not color_pair


@pytest.mark.parametrize(
    ("factor", "expected"),
    [(0, Color("#000000")), (0.5, Color("#7f7f7f")), (1, Color("#ffffff"))],
)
def test_shift_color_towards_interpolates_within_unit_interval(factor: float, expected: Color) -> None:
    """Shift colors only across the valid interpolation interval."""
    assert shift_color_towards(Color("#000000"), Color("#ffffff"), factor) == expected


@pytest.mark.parametrize("factor", [-0.1, 1.1])
def test_shift_color_towards_rejects_out_of_range_factor(factor: float) -> None:
    """Reject extrapolation factors before they can create invalid RGB channels."""
    with pytest.raises(ValueError, match="Factor must be between 0 and 1"):
        shift_color_towards(Color("#000000"), Color("#ffffff"), factor)


def test_gradient_zero_stops() -> None:
    with pytest.raises(ValueError, match="At least one stop must be provided"):
        Gradient()


def test_gradient_zero_steps() -> None:
    with pytest.raises(ValueError, match="Steps must be"):
        Gradient(Color("#ffffff"), steps=0)


def test_gradient_zero_steps_tuple() -> None:
    with pytest.raises(ValueError, match="Steps must be"):
        Gradient(Color("#ffffff"), Color("#000000"), Color("#ff0000"), steps=(1, 0))


@pytest.mark.parametrize("steps", [(), (0,), (-1,), (1, 0), (1, -1), (1, 2, 0)])
def test_gradient_rejects_empty_or_nonpositive_tuple_steps(steps: tuple[int, ...]) -> None:
    """Validate every tuple step before generation, including unused trailing values."""
    with pytest.raises(ValueError, match="Steps must be"):
        Gradient(Color("#ffffff"), Color("#000000"), steps=steps)


def test_gradient_repeats_valid_short_tuple_steps() -> None:
    """A valid short tuple retains its documented step-repetition behavior."""
    gradient = Gradient(Color("#ffffff"), Color("#000000"), Color("#ff0000"), steps=(2,))

    assert len(gradient.spectrum) == 5


@pytest.mark.parametrize(
    ("stops", "steps"),
    [
        ((Color("ffffff"), Color("000000")), (1, 2)),
        ((Color("ffffff"), Color("000000"), Color("ff0000")), (1, 2, 3)),
    ],
)
def test_gradient_rejects_step_tuples_longer_than_transition_count(
    stops: tuple[Color, ...],
    steps: tuple[int, ...],
) -> None:
    """Reject tuple entries that would otherwise be silently ignored."""
    with pytest.raises(ValueError, match="cannot contain more values"):
        Gradient(*stops, steps=steps)


def test_looping_gradient_counts_closing_transition_for_step_tuple() -> None:
    """Include the transition back to the first stop when validating tuple cardinality."""
    with pytest.raises(ValueError, match="cannot contain more values"):
        Gradient(Color("ffffff"), Color("000000"), steps=(1, 2, 3), loop=True)


@pytest.mark.parametrize("stop", ["ffffff", 15, None, object()])
def test_gradient_rejects_non_color_stops(stop: object) -> None:
    """Validate stops at the public constructor boundary."""
    with pytest.raises(TypeError, match="Stops must be Color instances"):
        Gradient(cast("Color", stop))


def test_gradient_slice() -> None:
    g = Gradient(Color("#ffffff"), Color("#000000"), steps=4)
    assert g[0] == Color("#ffffff")
    assert g[-1] == Color("#000000")
    assert g[1:3] == [Color("#bfbfbf"), Color("#808080")]


def test_gradient_interpolates_small_ascending_channel_deltas() -> None:
    gradient = Gradient(Color("#000000"), Color("#010101"), steps=10)

    assert [color.rgb_color for color in gradient] == ["000000"] * 6 + ["010101"] * 5


def test_gradient_does_not_overshoot_descending_channel_deltas() -> None:
    gradient = Gradient(Color("#909090"), Color("#808080"), steps=100)

    assert all(0x80 <= channel <= 0x90 for color in gradient for channel in color.rgb_ints)
    assert gradient[-2] == Color("#808080")


def test_gradient_iter() -> None:
    g = Gradient(Color("#ffffff"), Color("#000000"), steps=4)
    for color in g:
        assert isinstance(color, Color)


def test_gradient_str() -> None:
    g = Gradient(Color("#ffffff"), Color("#000000"), steps=4)
    assert "Stops(ffffff, 000000)" in str(g)


def test_gradient_len() -> None:
    g = Gradient(Color("#ffffff"), Color("#000000"), steps=4)
    assert len(g) == 5


def test_gradient_length_single_color() -> None:
    g = Gradient(Color("#ffffff"), steps=5)
    assert len(g.spectrum) == 1


def test_gradient_length_two_colors() -> None:
    g = Gradient(Color("#000000"), Color("#ffffff"), steps=5)
    assert len(g.spectrum) == 6


def test_gradient_length_three_colors() -> None:
    g = Gradient(Color("#000000"), Color("#ffffff"), Color("#000000"), steps=5)
    assert len(g.spectrum) == 11


def test_gradient_length_same_color_multiple_times() -> None:
    g = Gradient(Color("#ffffff"), Color("#ffffff"), Color("#ffffff"), Color("#ffffff"), steps=4)
    assert len(g.spectrum) == 13


def test_gradient_length_same_color_multiple_times_with_tuple_steps() -> None:
    g = Gradient(Color("#ffffff"), Color("#ffffff"), Color("#ffffff"), Color("#ffffff"), steps=(4, 6))
    assert len(g.spectrum) == 17


def test_gradient_single_color() -> None:
    g = Gradient(Color("#ffffff"), steps=5)
    assert g.spectrum == [Color("#ffffff")]


@pytest.mark.parametrize("steps", [(5,), (1, 3), (1, 2, 3)])
def test_gradient_single_color_accepts_tuple_step_values(steps: tuple[int, ...]) -> None:
    """Accept configuration tuples of any length when a single stop has no transitions."""
    assert Gradient(Color("#ffffff"), steps=steps).spectrum == [Color("#ffffff")]


def test_gradient_two_colors() -> None:
    g = Gradient(Color("#000000"), Color("#ffffff"), steps=3)
    assert g.spectrum[0] == Color("#000000")
    assert g.spectrum[-1] == Color("#ffffff")


def test_gradient_single_step() -> None:
    g = Gradient(Color("#ffffff"), steps=1)
    assert g.spectrum[0] == Color("#ffffff")


def test_gradient_three_colors() -> None:
    g = Gradient(Color("#ffffff"), Color("#000000"), Color("#ffffff"), steps=4)
    assert g.spectrum[0] == Color("#ffffff")
    assert g.spectrum[4] == Color("#000000")
    assert g.spectrum[-1] == Color("#ffffff")


def test_gradient_loop() -> None:
    g = Gradient(Color("#ffffff"), Color("#000000"), steps=4, loop=True)
    assert g.spectrum[-1] == Color("#ffffff")


def test_gradient_loop_preserves_source_stops() -> None:
    """Generate the closing transition without adding it to the stored source stops."""
    stops = (Color("#ffffff"), Color("#000000"))

    gradient = Gradient(*stops, steps=(2, 3), loop=True)

    assert gradient._stops == stops
    assert gradient.spectrum == [
        Color("#ffffff"),
        Color("#808080"),
        Color("#000000"),
        Color("#555555"),
        Color("#aaaaaa"),
        Color("#ffffff"),
    ]


def test_gradient_get_color_at_fraction() -> None:
    g = Gradient(Color("#ffffff"), Color("#000000"), steps=4)
    assert g.get_color_at_fraction(0) == Color("#ffffff")
    assert g.get_color_at_fraction(0.5) == Color("#808080")
    assert g.get_color_at_fraction(1) == Color("#000000")


@pytest.mark.parametrize("fraction", [-0.1, 1.1])
def test_gradient_get_color_at_fraction_rejects_out_of_range_values(fraction: float) -> None:
    g = Gradient(Color("#ffffff"), Color("#000000"), steps=4)
    with pytest.raises(ValueError, match="Fraction must be"):
        g.get_color_at_fraction(fraction)


@pytest.mark.parametrize(
    ("fraction", "expected_index"),
    [
        (0, 0),
        (math.nextafter(0.125, 0), 0),
        (0.125, 0),
        (math.nextafter(0.125, 1), 1),
        (math.nextafter(0.375, 0), 1),
        (0.375, 2),
        (math.nextafter(0.375, 1), 2),
        (math.nextafter(0.625, 0), 2),
        (0.625, 2),
        (math.nextafter(0.625, 1), 3),
        (math.nextafter(0.875, 0), 3),
        (0.875, 4),
        (math.nextafter(0.875, 1), 4),
        (1, 4),
    ],
)
def test_gradient_get_color_at_fraction_uses_nearest_sample(fraction: float, expected_index: int) -> None:
    """Select the nearest spectrum sample on both sides of every boundary."""
    gradient = Gradient(Color("#ffffff"), Color("#000000"), steps=4)

    assert gradient.get_color_at_fraction(fraction) == gradient[expected_index]


@pytest.mark.parametrize("fraction", [math.nan, math.inf, -math.inf])
def test_gradient_get_color_at_fraction_rejects_non_finite_values(fraction: float) -> None:
    """Reject non-finite fractions instead of returning a spectrum endpoint."""
    gradient = Gradient(Color("#ffffff"), Color("#000000"), steps=4)

    with pytest.raises(ValueError, match="Fraction must be finite"):
        gradient.get_color_at_fraction(fraction)


@pytest.mark.parametrize("fraction", [True, False, "0.5", None, object()])
def test_gradient_get_color_at_fraction_rejects_non_numeric_values(fraction: object) -> None:
    """Reject values outside the documented integer-or-float input contract."""
    gradient = Gradient(Color("#ffffff"), Color("#000000"), steps=4)

    with pytest.raises(TypeError, match="Fraction must be an integer or float"):
        gradient.get_color_at_fraction(cast("float", fraction))


@pytest.mark.parametrize("fraction", [0, 0.5, 1])
def test_gradient_get_color_at_fraction_supports_single_color_spectrum(fraction: float) -> None:
    """Return the only available color for every valid fraction."""
    gradient = Gradient(Color("#ffffff"), steps=1)

    assert gradient.get_color_at_fraction(fraction) == Color("#ffffff")


@pytest.mark.parametrize(
    "direction",
    [
        Gradient.Direction.DIAGONAL,
        Gradient.Direction.HORIZONTAL,
        Gradient.Direction.VERTICAL,
        Gradient.Direction.RADIAL,
    ],
)
def test_gradient_build_coordinate_color_mapping(direction: Gradient.Direction) -> None:
    g = Gradient(Color("#ffffff"), Color("#000000"), steps=4)
    coordinate_map = g.build_coordinate_color_mapping(1, 10, 1, 10, direction)
    if direction == Gradient.Direction.DIAGONAL:
        assert coordinate_map[Coord(1, 1)] == Color("#ffffff")
        assert coordinate_map[Coord(10, 10)] == Color("#000000")
    elif direction == Gradient.Direction.HORIZONTAL:
        assert coordinate_map[Coord(1, 1)] == Color("#ffffff")
        assert coordinate_map[Coord(10, 1)] == Color("#000000")
    elif direction == Gradient.Direction.VERTICAL:
        assert coordinate_map[Coord(1, 1)] == Color("#ffffff")
        assert coordinate_map[Coord(1, 10)] == Color("#000000")
    elif direction == Gradient.Direction.RADIAL:
        assert coordinate_map[Coord(5, 5)] == Color("#ffffff")
        assert coordinate_map[Coord(10, 10)] == Color("#000000")


@pytest.mark.parametrize(
    "direction",
    [
        Gradient.Direction.DIAGONAL,
        Gradient.Direction.HORIZONTAL,
        Gradient.Direction.VERTICAL,
        Gradient.Direction.RADIAL,
    ],
)
@pytest.mark.parametrize("min_column", [1, 5])
@pytest.mark.parametrize("max_column", [5, 10])
@pytest.mark.parametrize("min_row", [1, 5])
@pytest.mark.parametrize("max_row", [5, 10])
def test_gradient_build_coordinate_color_mapping_no_exceptions(
    direction: Gradient.Direction,
    min_column: int,
    max_column: int,
    min_row: int,
    max_row: int,
) -> None:
    g = Gradient(Color("#ffffff"), Color("#000000"), steps=4)
    if min_column > max_column or min_row > max_row:
        with pytest.raises(ValueError, match="must be less than or equal"):
            g.build_coordinate_color_mapping(min_row, max_row, min_column, max_column, direction)
    else:  # check for exceptions across single row/column and issue that might arise from math calculations
        g.build_coordinate_color_mapping(min_row, max_row, min_column, max_column, direction)


def test_gradient_build_coordinate_color_mapping_single_row() -> None:
    g = Gradient(Color("#ffffff"), Color("#000000"), steps=4)
    coordinate_map = g.build_coordinate_color_mapping(1, 1, 1, 10, Gradient.Direction.HORIZONTAL)
    assert coordinate_map[Coord(1, 1)] == Color("#ffffff")
    assert coordinate_map[Coord(10, 1)] == Color("#000000")


def test_gradient_build_coordinate_color_mapping_horizontal_respects_min_row() -> None:
    g = Gradient(Color("#ffffff"), Color("#000000"), steps=4)
    coordinate_map = g.build_coordinate_color_mapping(5, 10, 1, 10, Gradient.Direction.HORIZONTAL)
    assert Coord(1, 4) not in coordinate_map
    assert coordinate_map[Coord(1, 5)] == Color("#ffffff")
    assert coordinate_map[Coord(10, 10)] == Color("#000000")


def test_gradient_build_coordinate_color_mapping_single_column() -> None:
    g = Gradient(Color("#ffffff"), Color("#000000"), steps=4)
    coordinate_map = g.build_coordinate_color_mapping(1, 10, 1, 1, Gradient.Direction.VERTICAL)
    assert coordinate_map[Coord(1, 1)] == Color("#ffffff")
    assert coordinate_map[Coord(1, 10)] == Color("#000000")


def test_gradient_build_coordinate_color_mapping_single_row_column() -> None:
    g = Gradient(Color("#ffffff"), Color("#000000"), steps=4)
    coordinate_map = g.build_coordinate_color_mapping(1, 1, 1, 1, Gradient.Direction.HORIZONTAL)
    assert coordinate_map[Coord(1, 1)] == Color("#ffffff")


@pytest.mark.parametrize(
    "direction",
    [
        Gradient.Direction.DIAGONAL,
        Gradient.Direction.HORIZONTAL,
        Gradient.Direction.VERTICAL,
        Gradient.Direction.RADIAL,
    ],
)
def test_gradient_build_coordinate_color_mapping_single_cell_uses_first_color(
    direction: Gradient.Direction,
) -> None:
    """Use the first gradient color when a mapping has no directional span."""
    gradient = Gradient(Color("#ffffff"), Color("#000000"), steps=10)

    coordinate_map = gradient.build_coordinate_color_mapping(5, 5, 7, 7, direction)

    assert coordinate_map == {Coord(7, 5): Color("#ffffff")}


@pytest.mark.parametrize(
    ("direction", "max_row", "max_column"),
    [
        (Gradient.Direction.DIAGONAL, 2, 2),
        (Gradient.Direction.HORIZONTAL, 1, 2),
        (Gradient.Direction.VERTICAL, 2, 1),
    ],
)
def test_gradient_build_coordinate_color_mapping_two_cell_span_uses_both_stops(
    direction: Gradient.Direction,
    max_row: int,
    max_column: int,
) -> None:
    """Map exact endpoints correctly even when the spectrum is longer than the span."""
    gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=10)

    coordinate_map = gradient.build_coordinate_color_mapping(1, max_row, 1, max_column, direction)

    assert coordinate_map[Coord(1, 1)] == Color("#000000")
    assert coordinate_map[Coord(max_column, max_row)] == Color("#ffffff")


def test_gradient_build_coordinate_color_mapping_samples_entire_spectrum() -> None:
    """Map evenly spaced coordinates to every precomputed spectrum sample."""
    gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=4)

    coordinate_map = gradient.build_coordinate_color_mapping(1, 1, 1, 5, Gradient.Direction.HORIZONTAL)

    assert [coordinate_map[Coord(column, 1)] for column in range(1, 6)] == gradient.spectrum


@pytest.mark.parametrize(
    ("direction", "start", "end"),
    [
        (Gradient.Direction.DIAGONAL, Coord(7, 5), Coord(9, 7)),
        (Gradient.Direction.HORIZONTAL, Coord(7, 5), Coord(9, 5)),
        (Gradient.Direction.VERTICAL, Coord(7, 5), Coord(7, 7)),
        (Gradient.Direction.RADIAL, Coord(8, 6), Coord(7, 5)),
    ],
)
@pytest.mark.parametrize("steps", [2, 10])
def test_gradient_build_coordinate_color_mapping_offset_bounds_use_both_stops(
    direction: Gradient.Direction,
    start: Coord,
    end: Coord,
    steps: int,
) -> None:
    """Map both stops at offset bounds for spectra shorter and longer than the spans."""
    gradient = Gradient(Color("#000000"), Color("#ffffff"), steps=steps)

    coordinate_map = gradient.build_coordinate_color_mapping(5, 7, 7, 9, direction)

    assert coordinate_map[start] == Color("#000000")
    assert coordinate_map[end] == Color("#ffffff")


def test_gradient_build_coordinate_color_mapping_invalid_row_column() -> None:
    g = Gradient(Color("#ffffff"), Color("#000000"), steps=4)
    with pytest.raises(ValueError, match="must be greater than 0"):
        g.build_coordinate_color_mapping(0, 10, 0, 10, Gradient.Direction.HORIZONTAL)
    with pytest.raises(ValueError, match="must be greater than 0"):
        g.build_coordinate_color_mapping(10, 0, 10, 0, Gradient.Direction.HORIZONTAL)


def test_gradient_build_coordinate_color_mapping_max_less_than_min() -> None:
    g = Gradient(Color("#ffffff"), Color("#000000"), steps=4)
    with pytest.raises(ValueError, match="must be less than or equal"):
        g.build_coordinate_color_mapping(10, 1, 10, 1, Gradient.Direction.HORIZONTAL)


def test_color_invalid_xterm_color() -> None:
    with pytest.raises(ValueError, match="Invalid color value"):
        Color(256)


def test_color_invalid_hex_color() -> None:
    with pytest.raises(ValueError, match="Invalid color value"):
        Color("#ffffzz")


@pytest.mark.parametrize("color", [True, False, 1.0, b"ffffff", None, object()])
def test_color_rejects_values_other_than_non_boolean_ints_and_strings(color: object) -> None:
    """Reject values that could previously pass permissive numeric membership checks."""
    with pytest.raises(ValueError, match="Invalid color value"):
        Color(cast("int | str", color))


@pytest.mark.parametrize("color", [0, 255])
def test_color_accepts_xterm_range_endpoints(color: int) -> None:
    """Accept both inclusive endpoints of the XTerm-256 range."""
    assert Color(color).xterm_color == color


@pytest.mark.parametrize("color", ["1234567", "#1234567", "##123456"])
def test_color_rejects_malformed_hex_prefix_or_length(color: str) -> None:
    """Reject RGB strings that rendering would otherwise truncate or normalize."""
    with pytest.raises(ValueError, match="Invalid color value"):
        Color(color)


def test_color_valid_hex_with_hash() -> None:
    assert Color("#ffffff") == Color("#ffffff")


def test_color_hex_rgb_ints() -> None:
    assert Color("#000000").rgb_ints == (0, 0, 0)


def test_color_xterm_rgb_ints() -> None:
    assert Color(0).rgb_ints == (0, 0, 0)


def test_color_not_equal() -> None:
    assert Color("#ffffff") != Color("#000000")


def test_color_not_equal_different_types() -> None:
    assert Color("#ffffff") != 0
    assert Color(0) != "ffffff"


def test_color_is_hashable() -> None:
    hash(Color("#ffffff"))
    hash(Color(0))


@pytest.mark.parametrize(
    ("left", "right"),
    [("FFFFFF", "ffffff"), ("#FFFFFF", "ffffff"), ("#Ab12Cd", "ab12cd")],
)
def test_color_normalizes_equivalent_rgb_specifications(left: str, right: str) -> None:
    left_color = Color(left)
    right_color = Color(right)

    assert left_color == right_color
    assert hash(left_color) == hash(right_color)
    assert left_color.color_arg == right_color.color_arg == right


def test_color_identity_preserves_xterm_specification() -> None:
    xterm_zero = Color(0)
    xterm_sixteen = Color(16)
    rgb_black = Color("000000")

    assert xterm_zero.rgb_color == xterm_sixteen.rgb_color == rgb_black.rgb_color
    assert len({xterm_zero, xterm_sixteen, rgb_black}) == 3


@pytest.mark.parametrize(
    ("attribute", "value"),
    [("color_arg", "000000"), ("xterm_color", 0), ("rgb_color", "000000")],
)
def test_color_is_immutable(attribute: str, value: object) -> None:
    color = Color("ffffff")

    with pytest.raises(FrozenInstanceError):
        setattr(color, attribute, value)


def test_color_supports_deepcopy() -> None:
    color = Color("ABCDEF")

    copied_color = deepcopy(color)

    assert copied_color == color
    assert copied_color is not color


def test_color_is_iterable() -> None:
    assert list(Color("#ffffff")) == [Color("#ffffff")]


@pytest.mark.parametrize(
    ("color", "expected_repr"),
    [
        (Color("#ffffff"), "Color('ffffff')"),
        (Color(0), "Color(0)"),
        (Color(255), "Color(255)"),
    ],
)
def test_color_repr_round_trip(color: Color, expected_repr: str) -> None:
    """Represent RGB and XTerm colors with reconstructible constructor calls."""
    color_repr = repr(color)

    assert color_repr == expected_repr
    assert eval(color_repr, {"__builtins__": {}, "Color": Color}) == color  # noqa: S307


@pytest.mark.parametrize(
    ("color_pair", "expected_repr"),
    [
        (ColorPair(), "ColorPair(fg=None, bg=None)"),
        (ColorPair(fg=Color("ffffff")), "ColorPair(fg=Color('ffffff'), bg=None)"),
        (ColorPair(bg=Color(0)), "ColorPair(fg=None, bg=Color(0))"),
        (
            ColorPair(fg=Color(1), bg=Color("abcdef")),
            "ColorPair(fg=Color(1), bg=Color('abcdef'))",
        ),
    ],
)
def test_color_pair_repr_round_trip(color_pair: ColorPair, expected_repr: str) -> None:
    """Represent every foreground/background combination with valid constructor names."""
    color_pair_repr = repr(color_pair)

    assert color_pair_repr == expected_repr
    assert eval(  # noqa: S307
        color_pair_repr,
        {"__builtins__": {}, "Color": Color, "ColorPair": ColorPair},
    ) == color_pair


def test_color_str() -> None:
    assert "Color Code: ffffff" in str(Color("#ffffff"))


def test_color_str_includes_xterm_zero() -> None:
    assert "XTerm Color: 0" in str(Color(0))


def test_color_pair_str_includes_xterm_zero() -> None:
    color_pair = ColorPair(0, 0)
    color_pair_str = str(color_pair)
    assert "Foreground XTerm Color: 0" in color_pair_str
    assert "Background XTerm Color: 0" in color_pair_str
