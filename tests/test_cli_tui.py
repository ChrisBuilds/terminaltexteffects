"""CLI tests for opening the interactive interface."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

import terminaltexteffects.effects
from terminaltexteffects import __main__, tui
from terminaltexteffects.__main__ import _check_user_module_name, build_parser

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

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
        effect_dirs: Sequence[tuple[Path, str]] = (),
        effect_files: Mapping[str, Path] | None = None,
        check_name: object = None,
    ) -> None:
        calls.append(
            {
                "effects": effect_resource_map,
                "text": text,
                "input_file": input_file,
                "effect": effect,
                "effect_dirs": list(effect_dirs),
                "effect_files": dict(effect_files or {}),
                "check_name": check_name,
            },
        )

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
        {
            "effects": tui_calls[0]["effects"],
            "text": "from file",
            "input_file": str(source),
            "effect": "wipe",
            "effect_dirs": tui_calls[0]["effect_dirs"],
            "effect_files": tui_calls[0]["effect_files"],
            "check_name": tui_calls[0]["check_name"],
        },
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


def test_broken_development_effects_do_not_stop_the_tui(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tui_calls: list[dict[str, Any]],
) -> None:
    """The interface opens with the development directory, and lists its effects itself."""
    (tmp_path / "effect_broken.py").write_text('raise RuntimeError("unfinished")\n')
    (tmp_path / "effect_prototype.py").write_text(
        """from dataclasses import dataclass
from terminaltexteffects.effects.effect_wipe import Wipe, WipeConfig
from terminaltexteffects.utils import argutils

@dataclass
class PrototypeConfig(WipeConfig):
    parser_spec: argutils.ParserSpec = argutils.ParserSpec(
        name="prototype", help="Prototype", description="Prototype", epilog=""
    )

def get_effect_resources():
    return "prototype", Wipe, PrototypeConfig
""",
    )
    monkeypatch.setenv("TTE_DEV_EFFECTS_DIR", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty-config"))
    _set_terminals(monkeypatch, stdin=True, stdout=True)
    _run_main(monkeypatch, ["tte", "--tui", "prototype"])
    call = tui_calls[0]
    assert (tmp_path.resolve(), "_tte_dev_") in call["effect_dirs"]
    assert call["effect"] == "prototype"
    assert "prototype" in call["effects"]
    assert call["effect_files"]["prototype"] == (tmp_path / "effect_prototype.py").resolve()
    assert "wipe" in call["effects"]


def test_the_tui_watches_every_effect_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tui_calls: list[dict[str, Any]],
) -> None:
    """The interface watches the built-in and user effect directories, with the file of each built-in effect."""
    monkeypatch.delenv("TTE_DEV_EFFECTS_DIR", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    _set_terminals(monkeypatch, stdin=True, stdout=True)
    _run_main(monkeypatch, ["tte", "--tui"])
    call = tui_calls[0]
    builtin_dir = Path(terminaltexteffects.effects.__path__[0]).resolve()
    assert call["effect_dirs"] == [
        (builtin_dir, "terminaltexteffects.effects."),
        (tmp_path / "terminaltexteffects" / "effects", ""),
    ]
    assert call["effect_files"]["wipe"] == builtin_dir / "effect_wipe.py"
    assert call["check_name"] is _check_user_module_name


def test_broken_builtin_effects_do_not_stop_the_tui(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tui_calls: list[dict[str, Any]],
) -> None:
    """A built-in effect module that fails to import is left out, so the interface can list it in red."""
    (tmp_path / "effect_scratch.py").write_text('raise RuntimeError("unfinished")\n')
    monkeypatch.setattr(terminaltexteffects.effects, "__path__", [*terminaltexteffects.effects.__path__, str(tmp_path)])
    monkeypatch.delenv("TTE_DEV_EFFECTS_DIR", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty-config"))
    _set_terminals(monkeypatch, stdin=True, stdout=True)
    _run_main(monkeypatch, ["tte", "--tui"])
    assert "wipe" in tui_calls[0]["effects"]
    with pytest.raises(RuntimeError, match="unfinished"):
        build_parser()


def test_broken_development_effects_still_stop_an_effect_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Running an effect from the command line still reports a development effect that cannot be imported."""
    (tmp_path / "effect_broken.py").write_text('raise RuntimeError("unfinished")\n')
    monkeypatch.setenv("TTE_DEV_EFFECTS_DIR", str(tmp_path))
    monkeypatch.setattr(__main__.sys, "argv", ["tte", "wipe"])
    with pytest.raises(RuntimeError, match="unfinished"):
        __main__.build_parsers_and_parse_args()


@pytest.mark.parametrize("argv", [["tte", "--random-effect"], ["tte", "--export", "out.tterec"]])
def test_broken_development_effects_stop_runs_without_an_effect_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    argv: list[str],
) -> None:
    """Global-only runs that play an effect still report a development effect that cannot be imported."""
    (tmp_path / "effect_broken.py").write_text('raise RuntimeError("unfinished")\n')
    monkeypatch.setenv("TTE_DEV_EFFECTS_DIR", str(tmp_path))
    monkeypatch.setattr(__main__.sys, "argv", argv)
    with pytest.raises(RuntimeError, match="unfinished"):
        __main__.build_parsers_and_parse_args()


def test_development_module_that_exits_does_not_stop_the_tui(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A development module that calls sys.exit while importing is left out when the TUI may open."""
    (tmp_path / "effect_exits.py").write_text("import sys\nsys.exit(2)\n")
    monkeypatch.setenv("TTE_DEV_EFFECTS_DIR", str(tmp_path))
    monkeypatch.setattr(__main__.sys, "argv", ["tte", "--tui"])
    _, effects = __main__.build_parsers_and_parse_args()
    assert "wipe" in effects
