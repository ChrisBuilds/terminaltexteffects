"""Tests for easing functions and sequence progression."""

from __future__ import annotations

import math

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


def _reference_bezier(x1: float, y1: float, x2: float, y2: float, progress: float) -> float:
    """Invert the horizontal curve with bisection independently of the production solver."""
    lower, upper = 0.0, 1.0
    for _ in range(80):
        t = (lower + upper) / 2
        x = 3 * x1 * (1 - t) ** 2 * t + 3 * x2 * (1 - t) * t**2 + t**3
        if x == progress:
            return 3 * y1 * (1 - t) ** 2 * t + 3 * y2 * (1 - t) * t**2 + t**3
        if x < progress:
            lower = t
        else:
            upper = t
    t = (lower + upper) / 2
    return 3 * y1 * (1 - t) ** 2 * t + 3 * y2 * (1 - t) * t**2 + t**3


@pytest.mark.parametrize(
    "control_points",
    [(0, 0, 0, 1), (1, 0, 1, 1), (0, 0, 1, 1), (1, 0, 0, 1), (0, 1.6, 1, -0.6)],
)
@pytest.mark.parametrize("progress", [1e-9, 0.001, 0.002, 0.25, 0.5, 0.75, 0.998, 0.999, 1 - 1e-9])
def test_make_easing_matches_reference(
    control_points: tuple[float, float, float, float],
    progress: float,
) -> None:
    """Valid flat and ordinary curves agree with an independent inverse."""
    actual = easing.make_easing(*control_points)(progress)
    expected = _reference_bezier(*control_points, progress)
    assert actual == pytest.approx(expected, abs=1e-8)


@pytest.mark.parametrize("control_points", [(0, 0, 0, 1), (1, 0, 1, 1)])
def test_make_easing_flat_endpoints_are_monotonic(control_points: tuple[float, float, float, float]) -> None:
    """Flat horizontal endpoints do not reverse eased progress."""
    curve = easing.make_easing(*control_points)
    values = [curve(step / 1000) for step in range(1001)]
    assert values == sorted(values)


@pytest.mark.parametrize("invalid", [-0.1, 1.1, math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("position", [0, 2])
def test_make_easing_rejects_invalid_horizontal_control_points(invalid: float, position: int) -> None:
    """The horizontal curve must have a finite, single-valued inverse."""
    control_points = [0.25, 0.0, 0.75, 1.0]
    control_points[position] = invalid
    with pytest.raises(ValueError, match=f"x{1 if position == 0 else 2} must be finite and between 0 and 1"):
        easing.make_easing(*control_points)


def test_make_easing_allows_vertical_overshoot() -> None:
    """Vertical control points may legitimately exceed the unit interval."""
    curve = easing.make_easing(0, 2, 1, 2)
    assert curve(0.5) > 1


@pytest.mark.parametrize("clamp", [False, True])
@pytest.mark.parametrize("raw_value", [-0.5, 1.5])
def test_easing_tracker_clamp_matches_public_setting(*, clamp: bool, raw_value: float) -> None:
    """The public clamp setting controls current and subsequent steps."""
    tracker = easing.EasingTracker(lambda _: raw_value, total_steps=2, clamp=clamp)

    assert tracker.clamp is clamp
    assert tracker.step() == (min(1.0, max(0.0, raw_value)) if clamp else raw_value)

    tracker.clamp = not clamp
    assert tracker.step() == (raw_value if clamp else min(1.0, max(0.0, raw_value)))


@pytest.mark.parametrize("total_steps", [0, -1, 1.5, 2.0, True, False, "2", None])
@pytest.mark.parametrize("kind", ["tracker", "sequence"])
def test_easers_reject_invalid_step_counts(kind: str, total_steps: object) -> None:
    """Both public easers require a positive non-boolean integer step count."""
    if kind == "tracker":
        with pytest.raises(ValueError, match="total_steps must be a positive integer"):
            easing.EasingTracker(easing.linear, total_steps=total_steps)  # type: ignore[arg-type]
    else:
        with pytest.raises(ValueError, match="total_steps must be a positive integer"):
            easing.SequenceEaser([1, 2], easing.linear, total_steps=total_steps)  # type: ignore[arg-type]


def test_easers_accept_single_step() -> None:
    """A one-step easing completes and includes the entire sequence."""
    tracker = easing.EasingTracker(easing.linear, total_steps=1)
    sequence_easer = easing.SequenceEaser([1, 2], easing.linear, total_steps=1)

    assert list(tracker) == [1.0]
    assert sequence_easer.step() == [1, 2]
    assert sequence_easer.is_complete()


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
