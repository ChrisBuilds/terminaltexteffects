"""CLI tests for opening the interactive interface."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from terminaltexteffects import __main__, tui

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = [pytest.mark.smoke]


@pytest.fixture
def tui_calls(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Record interface launches instead of starting Textual."""
    calls: list[dict[str, Any]] = []

    def fake_run(
        effect_resource_map: dict[str, Any],
        text: str = "",
        input_file: str | None = None,
        effect: str | None = None,
    ) -> None:
        calls.append({"effects": effect_resource_map, "text": text, "input_file": input_file, "effect": effect})

    monkeypatch.setattr(tui, "run", fake_run)
    monkeypatch.setattr(tui, "is_available", lambda: True)
    return calls


def _set_terminals(monkeypatch: pytest.MonkeyPatch, *, stdin: bool, stdout: bool) -> None:
    monkeypatch.setattr(
        __main__,
        "_is_terminal",
        lambda stream: stdin if stream is __main__.sys.stdin else stdout,
    )


def _run_main(monkeypatch: pytest.MonkeyPatch, argv: list[str], piped: str = "") -> None:
    monkeypatch.setattr(__main__.sys, "argv", argv)
    monkeypatch.setattr(__main__.Terminal, "get_piped_input", lambda: piped)
    __main__.main()


def test_bare_tte_in_a_terminal_opens_the_tui(
    monkeypatch: pytest.MonkeyPatch,
    tui_calls: list[dict[str, Any]],
) -> None:
    """Running tte with no effect or input in a terminal should open the interface with empty text."""
    _set_terminals(monkeypatch, stdin=True, stdout=True)
    _run_main(monkeypatch, ["tte"])
    assert len(tui_calls) == 1
    assert tui_calls[0]["text"] == ""
    assert "decrypt" in tui_calls[0]["effects"]


def test_bare_tte_without_textual_prints_usage_and_install_hint(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tui_calls: list[dict[str, Any]],
) -> None:
    """Without Textual, bare tte should explain how to use it and install the interface."""
    monkeypatch.setattr(tui, "is_available", lambda: False)
    _set_terminals(monkeypatch, stdin=True, stdout=True)
    _run_main(monkeypatch, ["tte"])
    captured = capsys.readouterr()
    assert not tui_calls
    assert captured.out == ""
    assert "usage: tte" in captured.err
    assert tui.INSTALL_HINT in captured.err


def test_piped_input_without_effect_opens_the_tui_with_the_text(
    monkeypatch: pytest.MonkeyPatch,
    tui_calls: list[dict[str, Any]],
) -> None:
    """Piped input with no effect should load the text into the interface."""
    _set_terminals(monkeypatch, stdin=False, stdout=True)
    _run_main(monkeypatch, ["tte"], piped="hello")
    assert [call["text"] for call in tui_calls] == ["hello"]


def test_piped_input_without_effect_or_terminal_output_keeps_the_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tui_calls: list[dict[str, Any]],
) -> None:
    """Without a terminal for output, a missing effect should remain an error."""
    _set_terminals(monkeypatch, stdin=False, stdout=False)
    with pytest.raises(SystemExit) as exc_info:
        _run_main(monkeypatch, ["tte"], piped="hello")
    assert exc_info.value.code == 1
    assert not tui_calls
    assert "No effect specified" in capsys.readouterr().out


def test_missing_effect_error_mentions_the_tui_when_not_installed(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tui_calls: list[dict[str, Any]],
) -> None:
    """The missing-effect error should point to the interface when it is not installed."""
    monkeypatch.setattr(tui, "is_available", lambda: False)
    _set_terminals(monkeypatch, stdin=False, stdout=True)
    with pytest.raises(SystemExit):
        _run_main(monkeypatch, ["tte"], piped="hello")
    assert not tui_calls
    assert tui.INSTALL_HINT in capsys.readouterr().out


def test_empty_piped_input_without_effect_stays_silent(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tui_calls: list[dict[str, Any]],
) -> None:
    """Empty piped input should remain a silent no-op."""
    _set_terminals(monkeypatch, stdin=False, stdout=True)
    _run_main(monkeypatch, ["tte"], piped=" \n")
    assert not tui_calls
    assert capsys.readouterr() == ("", "")


def test_tui_flag_loads_input_file_and_selects_effect(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    tui_calls: list[dict[str, Any]],
) -> None:
    """--tui should load --input-file text and preselect a named effect."""
    source = tmp_path / "in.txt"
    source.write_text("from file", encoding="utf-8")
    _set_terminals(monkeypatch, stdin=True, stdout=True)
    _run_main(monkeypatch, ["tte", "--tui", "-i", str(source), "wipe"])
    assert tui_calls == [
        {"effects": tui_calls[0]["effects"], "text": "from file", "input_file": str(source), "effect": "wipe"},
    ]


@pytest.mark.parametrize(
    ("available", "stdout", "message"),
    [
        pytest.param(False, True, tui.INSTALL_HINT, id="not-installed"),
        pytest.param(True, False, "needs standard output to be a terminal", id="no-terminal"),
    ],
)
def test_tui_flag_errors_when_the_tui_cannot_open(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tui_calls: list[dict[str, Any]],
    *,
    available: bool,
    stdout: bool,
    message: str,
) -> None:
    """--tui should fail with status 1 when Textual is missing or output is not a terminal."""
    monkeypatch.setattr(tui, "is_available", lambda: available)
    _set_terminals(monkeypatch, stdin=True, stdout=stdout)
    with pytest.raises(SystemExit) as exc_info:
        _run_main(monkeypatch, ["tte", "--tui"])
    assert exc_info.value.code == 1
    assert not tui_calls
    assert message in capsys.readouterr().err


def test_effect_runs_are_unchanged(
    monkeypatch: pytest.MonkeyPatch,
    tui_calls: list[dict[str, Any]],
) -> None:
    """Naming an effect should play it rather than open the interface."""
    _set_terminals(monkeypatch, stdin=False, stdout=True)
    played: list[str] = []
    monkeypatch.setattr(__main__, "_print_replays", lambda *_args, **_kwargs: played.append("played"))
    _run_main(monkeypatch, ["tte", "wipe"], piped="hello")
    assert not tui_calls
    assert played == ["played"]
