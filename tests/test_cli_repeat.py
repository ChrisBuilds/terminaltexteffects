"""CLI replay counts and terminal cleanup without real-time animation waits."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from terminaltexteffects import __main__
from terminaltexteffects.effects.effect_expand import ExpandConfig
from terminaltexteffects.effects.effect_wipe import Wipe, WipeConfig
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
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


def test_repeat_iterator_creation_interrupt_restores_cursor(monkeypatch: pytest.MonkeyPatch) -> None:
    """An interruption while creating the next iterator still restores the terminal."""
    original_iterator = Wipe.__iter__
    iterator_count = 0
    restore = Mock()

    def create_iterator(effect: Wipe) -> Iterator[str]:
        nonlocal iterator_count
        iterator_count += 1
        if iterator_count == 2:
            raise KeyboardInterrupt
        return original_iterator(effect)

    monkeypatch.setattr(Wipe, "__iter__", create_iterator)
    monkeypatch.setattr(Terminal, "get_piped_input", lambda: "Hello")
    monkeypatch.setattr(Terminal, "prep_canvas", Mock())
    monkeypatch.setattr(Terminal, "restore_cursor", restore)
    monkeypatch.setattr(Terminal, "print", Mock())
    monkeypatch.setattr(sys, "argv", ["tte", "--repeat", "0", "--frame-rate", "0", "wipe"])
    with pytest.raises(SystemExit) as error:
        __main__.main()
    assert error.value.code == 1
    assert iterator_count == 2
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
        frames: list[str] = []
        playbacks.append(frames)
        for frame in original_iterator(effect):
            frames.append(frame)
            yield frame

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


def test_repeat_freezes_geometry_after_resize(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replay frames keep the prepared canvas dimensions after terminal resize."""
    original_iterator = Wipe.__iter__
    iterator_geometry: list[tuple[int, int]] = []
    size_probes = iter([(20, 2), (20, 4)])

    def record_iterator(effect: Wipe) -> Iterator[str]:
        iterator = original_iterator(effect)
        iterator_geometry.append((iterator.terminal._terminal_height, iterator.terminal.canvas.height))
        return iterator

    monkeypatch.setattr(Wipe, "__iter__", record_iterator)
    monkeypatch.setattr(Terminal, "_get_terminal_dimensions", lambda *_: next(size_probes))
    monkeypatch.setattr(Terminal, "get_piped_input", lambda: "a\nb\nc\nd")
    monkeypatch.setattr(Terminal, "prep_canvas", Mock())
    monkeypatch.setattr(Terminal, "restore_cursor", Mock())
    monkeypatch.setattr(Terminal, "print", Mock())
    monkeypatch.setattr(sys, "argv", ["tte", "--canvas-height", "0", "--frame-rate", "0", "--repeat", "2", "wipe"])
    __main__.main()
    assert iterator_geometry == [(2, 2), (2, 2)]


@pytest.mark.parametrize("filter_mode", ["include", "exclude"])
def test_random_repeat_selects_each_cycle_from_filtered_pool_with_defaults(
    monkeypatch: pytest.MonkeyPatch,
    filter_mode: str,
) -> None:
    """Random replay reselects per cycle with defaults and stable geometry."""
    parser, full_effect_map = __main__.build_parser(include_user_effects=False)
    expected_names = {"wipe", "expand"}
    if filter_mode == "include":
        filter_args = ["--include-effects", "wipe", "expand"]
    else:
        excluded_names = [name for name in full_effect_map if name not in expected_names]
        filter_args = ["--exclude-effects", *excluded_names]
    args = parser.parse_args(
        [
            "--seed",
            "17",
            "--frame-rate",
            "0",
            "--canvas-height",
            "0",
            "--repeat",
            "3",
            "--random-effect",
            *filter_args,
        ],
    )
    monkeypatch.setattr(__main__, "build_parsers_and_parse_args", lambda: (args, full_effect_map))
    expected_pool = [name for name in full_effect_map if name in expected_names]

    original_choice = __main__.random.choice
    choices_by_run: list[list[tuple[tuple[str, ...], str]]] = []
    current_choices: list[tuple[tuple[str, ...], str]] = []

    def record_choice(pool: list[str]) -> str:
        choice = original_choice(pool)
        current_choices.append((tuple(pool), choice))
        return choice

    monkeypatch.setattr(__main__.random, "choice", record_choice)
    original_iterator = BaseEffect.__iter__
    iterator_batches: list[list[tuple[BaseEffect, BaseEffectIterator]]] = []
    current_iterators: list[tuple[BaseEffect, BaseEffectIterator]] = []

    def record_iterator(effect: BaseEffect) -> BaseEffectIterator:
        iterator = original_iterator(effect)
        current_iterators.append((effect, iterator))
        return iterator

    monkeypatch.setattr(BaseEffect, "__iter__", record_iterator)
    size_probes = iter([(20, 2), (20, 4)])
    monkeypatch.setattr(Terminal, "_get_terminal_dimensions", lambda *_: next(size_probes))
    monkeypatch.setattr(Terminal, "get_piped_input", lambda: "A\nB\nC\nD")
    prepare, restore, output = Mock(), Mock(), Mock()
    monkeypatch.setattr(Terminal, "prep_canvas", prepare)
    monkeypatch.setattr(Terminal, "restore_cursor", restore)
    monkeypatch.setattr(Terminal, "print", output)

    for _ in range(2):
        current_choices = []
        current_iterators = []
        __main__.main()
        choices_by_run.append(current_choices)
        iterator_batches.append(current_iterators)

    expected_configs = {"Wipe": WipeConfig._build_config(), "Expand": ExpandConfig._build_config()}
    assert all(len(batch) == 3 for batch in choices_by_run)
    assert choices_by_run[0] == choices_by_run[1]
    assert all(
        pool == tuple(expected_pool) and choice in expected_names for batch in choices_by_run for pool, choice in batch
    )
    assert all(
        [type(effect).__name__.lower() for effect, _ in batch] == [choice for _, choice in choices]
        for batch, choices in zip(iterator_batches, choices_by_run, strict=True)
    )
    assert all(len({id(effect) for effect, _ in batch}) == 3 for batch in iterator_batches)
    for run_index, batch in enumerate(iterator_batches):
        expected_height = 2 if run_index == 0 else 4
        assert all(effect.input_data == "A\nB\nC\nD" for effect, _ in batch)
        assert all(effect.effect_config == expected_configs[type(effect).__name__] for effect, _ in batch)
        assert [(iterator.terminal._terminal_height, iterator.terminal.canvas.height) for _, iterator in batch] == [
            (expected_height, expected_height)
        ] * 3
    assert prepare.call_count == 2
    assert restore.call_count == 2
    assert output.call_count > 0


def test_random_repeat_until_interrupt_restores_cursor(monkeypatch: pytest.MonkeyPatch) -> None:
    """Continuous random replay selects again each cycle and restores the cursor on interruption."""
    choice = Mock(side_effect=["wipe", "expand", KeyboardInterrupt])
    restore = Mock()
    monkeypatch.setattr(__main__.random, "choice", choice)
    monkeypatch.setattr(Terminal, "get_piped_input", lambda: "A")
    monkeypatch.setattr(Terminal, "prep_canvas", Mock())
    monkeypatch.setattr(Terminal, "restore_cursor", restore)
    monkeypatch.setattr(Terminal, "print", Mock())
    monkeypatch.setattr(sys, "argv", ["tte", "--frame-rate", "0", "--repeat", "0", "--random-effect"])
    with pytest.raises(SystemExit) as error:
        __main__.main()
    assert error.value.code == 1
    assert choice.call_count == 3
    restore.assert_called_once()


def test_repeat_empty_input_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    """Continuous replay of whitespace-only input still exits successfully."""
    iterator = Mock(side_effect=AssertionError("unexpected animation"))
    monkeypatch.setattr(Wipe, "__iter__", iterator)
    monkeypatch.setattr(Terminal, "get_piped_input", lambda: " \n\t ")
    monkeypatch.setattr(sys, "argv", ["tte", "--repeat", "0", "wipe"])
    __main__.main()
    iterator.assert_not_called()
