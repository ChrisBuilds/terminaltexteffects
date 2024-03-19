from terminaltexteffects.utils.graphics import Gradient


def test_gradient_length_single_color() -> None:
    g = Gradient("ffffff", steps=5)
    assert len(g.spectrum) == 5


def test_gradient_length_two_colors() -> None:
    g = Gradient("000000", "ffffff", steps=5)
    assert len(g.spectrum) == 6


def test_gradient_length_three_colors() -> None:
    g = Gradient("000000", "ffffff", "000000", steps=5)
    assert len(g.spectrum) == 11


def test_gradient_length_same_color_multiple_times() -> None:
    g = Gradient("ffffff", "ffffff", "ffffff", "ffffff", steps=4)
    assert len(g.spectrum) == 13


def test_gradient_length_same_color_multiple_times_with_tuple_steps() -> None:
    g = Gradient("ffffff", "ffffff", "ffffff", "ffffff", steps=(4, 6))
    assert len(g.spectrum) == 17


def test_gradient_single_color() -> None:
    g = Gradient("ffffff", steps=5)
    assert all(color == "ffffff" for color in g.spectrum)


def test_gradient_two_colors() -> None:
    g = Gradient("000000", "ffffff", steps=3)
    assert g.spectrum[0] == "000000" and g.spectrum[-1] == "ffffff"


def test_gradient_single_step() -> None:
    g = Gradient("ffffff", steps=1)
    assert g.spectrum[0] == "ffffff"


def test_gradient_three_colors() -> None:
    g = Gradient("ffffff", "000000", "ffffff", steps=4)
    assert g.spectrum[0] == "ffffff" and g.spectrum[4] == "000000" and g.spectrum[-1] == "ffffff"
