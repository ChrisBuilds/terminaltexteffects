import pytest

from terminaltexteffects.utils.easing import eased_step_function

pytestmark = [pytest.mark.utils, pytest.mark.smoke]


def test_ease_valid_progress(easing_function_1):
    assert round(easing_function_1(0)) == 0
    assert round(easing_function_1(1)) == 1


@pytest.mark.parametrize("progress", [n / 10 for n in range(1, 11)])
def test_ease_progress_ratios(progress, easing_function_1):
    easing_function_1(progress)  # should not raise an exception


@pytest.mark.parametrize("clamp", [True, False])
def test_eased_step_function(easing_function_1, clamp):
    f = eased_step_function(easing_function_1, 0.01, clamp=clamp)
    used_step = 0
    while used_step < 1:
        used_step, eased_value = f()
        if clamp:
            assert 0 <= eased_value <= 1


@pytest.mark.parametrize("step_size", [-1, 0, 1.1])
def test_eased_step_function_invalid_step_size(easing_function_1, step_size):
    with pytest.raises(ValueError):
        _ = eased_step_function(easing_function_1, step_size)
