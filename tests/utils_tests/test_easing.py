import pytest

pytestmark = [pytest.mark.utils, pytest.mark.smoke]


def test_ease_valid_progress(easing_function_1) -> None:
    assert round(easing_function_1(0)) == 0
    assert round(easing_function_1(1)) == 1


@pytest.mark.parametrize("progress", [n / 10 for n in range(1, 11)])
def test_ease_progress_ratios(progress, easing_function_1) -> None:
    easing_function_1(progress)  # should not raise an exception
