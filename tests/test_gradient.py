from terminaltexteffects.utils.graphics import Color, Gradient


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
