"""CLI replay counts and terminal cleanup without real-time animation waits."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from terminaltexteffects import __main__
from terminaltexteffects.effects.effect_wipe import Wipe
from terminaltexteffects.engine.terminal import Terminal

if TYPE_CHECKING:
    from collections.abc import Iterator

pytestmark = [pytest.mark.smoke]


@pytest.mark.parametrize("count", [0, 1, 3])
def test_repeat_parser(count: int) -> None:
    """Accept non-negative playback counts and preserve the default."""
    parser, _ = __main__.build_parser(include_user_effects=False)
    assert parser.parse_args(["--repeat", str(count), "wipe"]).repeat == count
    assert parser.parse_args(["wipe"]).repeat == 1


@pytest.mark.parametrize("count", ["-1", "1.5", "abc"])
def test_repeat_parser_rejects_invalid_counts(count: str) -> None:
    """Invalid counts fail during argument parsing, before any animation."""
    parser, _ = __main__.build_parser(include_user_effects=False)
    with pytest.raises(SystemExit) as error:
        parser.parse_args(["--repeat", count, "wipe"])
    assert error.value.code == 2


@pytest.mark.parametrize("count", [None, 1, 3])
def test_repeat_fresh_iterators(monkeypatch: pytest.MonkeyPatch, count: int | None) -> None:
    """Each playback starts fresh while the output context opens only once."""
    iterator = Mock(side_effect=lambda: iter(["first", "last"]))
    output, prepare, restore = Mock(), Mock(), Mock()
    monkeypatch.setattr(Wipe, "__iter__", iterator)
    monkeypatch.setattr(Terminal, "get_piped_input", lambda: "Hello")
    monkeypatch.setattr(Terminal, "prep_canvas", prepare)
    monkeypatch.setattr(Terminal, "restore_cursor", restore)
    monkeypatch.setattr(Terminal, "print", output)
    arguments = ["tte", "wipe"] if count is None else ["tte", "--repeat", str(count), "wipe"]
    monkeypatch.setattr(sys, "argv", arguments)
    __main__.main()
    expected = 1 if count is None else count
    assert iterator.call_count == expected
    assert [call.args[0] for call in output.call_args_list] == ["first", "last"] * expected
    prepare.assert_called_once()
    restore.assert_called_once()


def test_repeat_infinite_interrupt_restores_cursor(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ctrl+C ends continuous replay and still restores the terminal."""
    iterator = Mock(side_effect=lambda: iter(["first", "last"]))
    output = Mock(side_effect=[None, None, None, KeyboardInterrupt])
    restore = Mock()
    monkeypatch.setattr(Wipe, "__iter__", iterator)
    monkeypatch.setattr(Terminal, "get_piped_input", lambda: "Hello")
    monkeypatch.setattr(Terminal, "prep_canvas", Mock())
    monkeypatch.setattr(Terminal, "restore_cursor", restore)
    monkeypatch.setattr(Terminal, "print", output)
    monkeypatch.setattr(sys, "argv", ["tte", "--repeat", "0", "wipe"])
    with pytest.raises(SystemExit) as error:
        __main__.main()
    assert error.value.code == 1
    assert iterator.call_count == 2
    restore.assert_called_once()


def test_repeat_zero_frames_stops(monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty plugin iterator cannot cause an infinite busy loop."""
    iterator = Mock(side_effect=[iter([]), AssertionError("unexpected replay")])
    monkeypatch.setattr(Wipe, "__iter__", iterator)
    monkeypatch.setattr(Terminal, "get_piped_input", lambda: "Hello")
    monkeypatch.setattr(Terminal, "prep_canvas", Mock())
    monkeypatch.setattr(Terminal, "restore_cursor", Mock())
    monkeypatch.setattr(sys, "argv", ["tte", "--repeat", "0", "wipe"])
    __main__.main()
    iterator.assert_called_once()


def test_repeat_real_wipe(monkeypatch: pytest.MonkeyPatch) -> None:
    """A real effect resets its frame sequence for each playback."""
    original_iterator = Wipe.__iter__
    playbacks: list[list[str]] = []

    def record_iterator(effect: Wipe) -> Iterator[str]:
        frames = list(original_iterator(effect))
        playbacks.append(frames)
        return iter(frames)

    output = Mock()
    monkeypatch.setattr(Wipe, "__iter__", record_iterator)
    monkeypatch.setattr(Terminal, "get_piped_input", lambda: "Hello")
    monkeypatch.setattr(Terminal, "prep_canvas", Mock())
    monkeypatch.setattr(Terminal, "restore_cursor", Mock())
    monkeypatch.setattr(Terminal, "print", output)
    monkeypatch.setattr(sys, "argv", ["tte", "--frame-rate", "0", "--repeat", "2", "wipe"])
    __main__.main()
    assert len(playbacks) == 2
    assert playbacks[0]
    assert playbacks[0] == playbacks[1]
    assert output.call_count == sum(map(len, playbacks))


def test_repeat_random_effect_selected_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Random replay chooses the effect once rather than choosing each cycle."""
    choice = Mock(return_value="wipe")
    iterator = Mock(side_effect=lambda: iter(["frame"]))
    monkeypatch.setattr(__main__.random, "choice", choice)
    monkeypatch.setattr(Wipe, "__iter__", iterator)
    monkeypatch.setattr(Terminal, "get_piped_input", lambda: "Hello")
    monkeypatch.setattr(Terminal, "prep_canvas", Mock())
    monkeypatch.setattr(Terminal, "restore_cursor", Mock())
    monkeypatch.setattr(Terminal, "print", Mock())
    monkeypatch.setattr(sys, "argv", ["tte", "--repeat", "2", "--random-effect"])
    __main__.main()
    choice.assert_called_once()
    assert iterator.call_count == 2


def test_repeat_empty_input_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    """Continuous replay of whitespace-only input still exits successfully."""
    iterator = Mock(side_effect=AssertionError("unexpected animation"))
    monkeypatch.setattr(Wipe, "__iter__", iterator)
    monkeypatch.setattr(Terminal, "get_piped_input", lambda: " \n\t ")
    monkeypatch.setattr(sys, "argv", ["tte", "--repeat", "0", "wipe"])
    __main__.main()
    iterator.assert_not_called()
