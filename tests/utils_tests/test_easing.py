"""Tests for easing functions and sequence progression."""

import pytest

from terminaltexteffects.utils import easing

pytestmark = [pytest.mark.utils, pytest.mark.smoke]


def test_ease_valid_progress(easing_function_1: easing.EasingFunction) -> None:
    """Easing functions begin and end at the expected values."""
    assert round(easing_function_1(0)) == 0
    assert round(easing_function_1(1)) == 1


@pytest.mark.parametrize("progress", [n / 10 for n in range(1, 11)])
def test_ease_progress_ratios(progress: float, easing_function_1: easing.EasingFunction) -> None:
    """Easing functions accept progress ratios throughout their domain."""
    easing_function_1(progress)  # should not raise an exception


@pytest.mark.parametrize("easing_function", [easing.in_sine, easing.in_back, easing.linear, easing.out_bounce])
@pytest.mark.parametrize("sequence_length", [1, 10, 100])
def test_sequence_easer_includes_final_element(easing_function: easing.EasingFunction, sequence_length: int) -> None:
    """A completed sequence includes its final element exactly once."""
    sequence = list(range(sequence_length))
    easer = easing.SequenceEaser(sequence, easing_function, total_steps=10)

    while not easer.is_complete():
        previous_total = list(easer.total)
        added = easer.step()
        assert added == easer.added
        if easer.is_complete():
            assert easer.total == sequence
            assert easer.added == sequence[len(previous_total) :]

    assert easer.step() == []
    assert easer.added == []
    assert easer.total == sequence


def test_sequence_easer_preserves_partial_final_ease() -> None:
    """An ease that ends below one keeps its partial final sequence."""
    sequence = list(range(10))
    easer = easing.SequenceEaser(sequence, lambda _: 0.9, total_steps=2)

    while not easer.is_complete():
        easer.step()

    assert easer.total == sequence[:9]
