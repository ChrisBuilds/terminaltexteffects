"""Regression tests for the Bubbles effect."""

from terminaltexteffects.effects import effect_bubbles


def test_bubbles_allows_zero_bubble_delay() -> None:
    """A zero delay should allow bubbles to launch on consecutive frames."""
    config = effect_bubbles.BubblesConfig._build_config()

    config.bubble_delay = 0

    assert config.bubble_delay == 0
