"""Tests for framework-level effect construction behavior."""

from __future__ import annotations

import pytest

from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.exceptions import EmptyInputError

pytestmark = [pytest.mark.engine, pytest.mark.smoke]


class _TestEffectIterator(BaseEffectIterator[BaseConfig]):
    """Minimal concrete iterator for testing base construction."""

    def __next__(self) -> str:
        raise StopIteration


class _TestEffect(BaseEffect[BaseConfig]):
    """Minimal concrete effect for testing base construction."""

    @property
    def _config_cls(self) -> type[BaseConfig]:
        return BaseConfig

    @property
    def _iterator_cls(self) -> type[BaseEffectIterator]:
        return _TestEffectIterator


@pytest.mark.parametrize(
    ("input_data", "canvas_width"),
    [
        pytest.param("   ", None, id="whitespace-only"),
        pytest.param("\x1b[0m", None, id="ansi-only"),
        pytest.param("   X", 1, id="fully-clipped"),
    ],
)
def test_effect_iterator_rejects_empty_renderable_input(input_data: str, canvas_width: int | None) -> None:
    """Effects raise a consistent error when the terminal has no visible input characters."""
    terminal_config = TerminalConfig._build_config()
    if canvas_width is not None:
        terminal_config.canvas_width = canvas_width

    with pytest.raises(EmptyInputError, match="no visible characters"):
        iter(_TestEffect(input_data, terminal_config=terminal_config))


def test_effect_iterator_accepts_ansi_styled_space() -> None:
    """Input spaces with visible ANSI background styling remain valid effect input."""
    effect_iterator = iter(_TestEffect("\x1b[48;5;1m \x1b[0m"))

    assert len(effect_iterator.terminal.get_characters()) == 1
