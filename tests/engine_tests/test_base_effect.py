"""Tests for framework-level effect construction behavior."""

from __future__ import annotations

import pytest

from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
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
        pytest.param("", None, id="empty"),
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


def test_terminal_output_before_iterator_reuses_terminal() -> None:
    """A context-created terminal becomes the next iterator's character graph."""
    effect = _TestEffect("A")

    with effect.terminal_output() as terminal:
        effect_iterator = iter(effect)

        assert effect_iterator.terminal is terminal


def test_iterator_before_terminal_output_reuses_terminal() -> None:
    """An iterator-created terminal becomes the next output context's terminal."""
    effect = _TestEffect("A")
    effect_iterator = iter(effect)

    with effect.terminal_output() as terminal:
        assert terminal is effect_iterator.terminal


def test_each_iterator_remains_fresh_inside_terminal_output() -> None:
    """Only the first iterator in a context consumes its staged terminal."""
    effect = _TestEffect("A")

    with effect.terminal_output() as terminal:
        first_iterator = iter(effect)
        second_iterator = iter(effect)

        assert first_iterator is not second_iterator
        assert first_iterator.terminal is terminal
        assert second_iterator.terminal is not terminal
        assert second_iterator.terminal is not first_iterator.terminal


def test_repeated_terminal_output_contexts_use_fresh_terminals() -> None:
    """Completed output contexts do not leak their terminal into later runs."""
    effect = _TestEffect("A")

    with effect.terminal_output() as first_terminal:
        first_iterator = iter(effect)
    with effect.terminal_output() as second_terminal:
        second_iterator = iter(effect)

    assert first_terminal is first_iterator.terminal
    assert second_terminal is second_iterator.terminal
    assert second_terminal is not first_terminal


def test_nested_terminal_output_contexts_pair_with_nearest_iterator() -> None:
    """Nested contexts independently stage terminals in last-in-first-out order."""
    effect = _TestEffect("A")

    with effect.terminal_output() as outer_terminal:
        with effect.terminal_output() as inner_terminal:
            inner_iterator = iter(effect)
        outer_iterator = iter(effect)

    assert inner_iterator.terminal is inner_terminal
    assert outer_iterator.terminal is outer_terminal
    assert inner_terminal is not outer_terminal


def test_terminal_output_restores_its_terminal_after_body_exception(capsys: pytest.CaptureFixture[str]) -> None:
    """Output cleanup still runs when user code raises inside the context."""
    effect = _TestEffect("A")
    message = "boom"

    with pytest.raises(RuntimeError, match="boom"), effect.terminal_output(end_symbol="done"):
        raise RuntimeError(message)

    assert capsys.readouterr().out.endswith("done")


def test_terminal_output_and_iterator_share_detected_dimensions(monkeypatch: pytest.MonkeyPatch) -> None:
    """A context and its iterator use one terminal-dimension snapshot."""
    detected_dimensions = iter([(80, 24), (40, 12)])
    monkeypatch.setattr(Terminal, "_get_terminal_dimensions", lambda _: next(detected_dimensions))
    effect = _TestEffect("A")

    with effect.terminal_output() as terminal:
        effect_iterator = iter(effect)

    assert effect_iterator.terminal is terminal
    assert (terminal._terminal_width, terminal._terminal_height) == (80, 24)
    assert next(detected_dimensions) == (40, 12)
