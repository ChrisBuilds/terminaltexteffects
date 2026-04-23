"""CLI tests for completion generation and parser wiring."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from terminaltexteffects import __main__

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = [pytest.mark.smoke]


def _write_demo_plugin(tmp_path: Path) -> None:
    """Create a simple plugin effect in a temporary XDG config directory."""
    plugin_dir = tmp_path / "terminaltexteffects" / "effects"
    plugin_dir.mkdir(parents=True)
    plugin_file = plugin_dir / "plugin_demo.py"
    plugin_file.write_text(
        """
from dataclasses import dataclass

from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.utils import argutils


class PluginDemoEffect:
    pass


@dataclass
class PluginDemoConfig(BaseConfig):
    parser_spec: argutils.ParserSpec = argutils.ParserSpec(
        name="plugindemo",
        help="plugin help",
        description="plugin description",
        epilog="plugin epilog",
    )
    plugin_speed: int = argutils.ArgSpec(name="--plugin-speed", default=1, type=int)


def get_effect_resources():
    return "plugindemo", PluginDemoEffect, PluginDemoConfig
""".strip(),
        encoding="utf-8",
    )


def _run_bash(script: str, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run a clean bash shell command in the project root."""
    bash_env = os.environ.copy()
    if env:
        bash_env.update(env)
    return subprocess.run(  # noqa: S603
        ["/bin/bash", "--noprofile", "--norc", "-c", script],
        check=True,
        capture_output=True,
        text=True,
        cwd=str(__main__.Path(__file__).resolve().parents[1]),
        env=bash_env,
    )


def _run_zsh(script: str, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run a clean zsh shell command in the project root."""
    zsh_env = os.environ.copy()
    if env:
        zsh_env.update(env)
    return subprocess.run(  # noqa: S603
        ["/bin/zsh", "-fc", script],
        check=True,
        capture_output=True,
        text=True,
        cwd=str(__main__.Path(__file__).resolve().parents[1]),
        env=zsh_env,
    )


def test_build_parser_registers_effects() -> None:
    """The parser builder should expose built-in effects as subcommands."""
    parser, effect_resource_map = __main__.build_parser()

    assert "matrix" in effect_resource_map
    assert "highlight" in effect_resource_map

    help_output = parser.format_help()
    assert "matrix" in help_output
    assert "highlight" in help_output


def test_main_print_completion_bash_outputs_script(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Printing bash completion should not require stdin or an effect."""
    monkeypatch.setattr(__main__.sys, "argv", ["tte", "--print-completion", "bash"])

    __main__.main()

    output = capsys.readouterr().out
    assert "complete -F _tte_completion tte" in output
    assert "--wrap-text" in output
    assert "--random-effect" in output
    assert "--include-effects" in output
    assert "matrix" in output
    assert "laseretch" in output
    assert "highlight" in output
    assert "--highlight-brightness" in output
    assert "--rain-color-gradient" in output


def test_main_print_completion_zsh_outputs_script(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Printing zsh completion should emit a zsh-loadable wrapper."""
    monkeypatch.setattr(__main__.sys, "argv", ["tte", "--print-completion", "zsh"])

    __main__.main()

    output = capsys.readouterr().out
    assert "autoload -Uz compinit bashcompinit" in output
    assert "bashcompinit" in output
    assert "complete -F _tte_completion tte" in output


def test_main_print_completion_invalid_shell_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid shell names should fail through argparse validation."""
    monkeypatch.setattr(__main__.sys, "argv", ["tte", "--print-completion", "fish"])

    with pytest.raises(SystemExit, match="2"):
        __main__.main()


def test_main_unsupported_ansi_sequence_exits_with_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Unsupported terminal control sequences should fail cleanly before rendering."""
    monkeypatch.setattr(__main__.sys, "argv", ["tte", "rain"])
    monkeypatch.setattr(__main__.Terminal, "get_piped_input", lambda: "abc\x1b[2Jdef")

    with pytest.raises(SystemExit) as exc_info:
        __main__.main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Unsupported ANSI/control sequence" in captured.err
    assert "\\x1b[2J" in captured.err


def test_build_parser_includes_plugin_effect_in_completion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Plugin-discovered effects should appear in generated completion output."""
    _write_demo_plugin(tmp_path)

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(__main__.sys, "argv", ["tte", "--print-completion", "bash"])

    __main__.main()

    output = capsys.readouterr().out
    assert "plugindemo" in output
    assert "--plugin-speed" in output


def test_bash_completion_registers_in_clean_shell() -> None:
    """The bash completion script should register both CLI entry points."""
    result = _run_bash(
        'eval "$('
        f"{sys.executable} -m terminaltexteffects --print-completion bash"
        ')"; complete -p tte; complete -p terminaltexteffects',
    )

    assert "complete -F _tte_completion tte" in result.stdout
    assert "complete -F _tte_completion terminaltexteffects" in result.stdout


def test_zsh_completion_registers_in_clean_shell() -> None:
    """The zsh completion script should self-bootstrap in a clean shell."""
    result = _run_zsh(
        'eval "$('
        f"{sys.executable} -m terminaltexteffects --print-completion zsh"
        ')"; whence -w _tte_completion; complete -p tte; complete -p terminaltexteffects',
    )

    assert "_tte_completion: function" in result.stdout
    assert "complete -F _tte_completion tte" in result.stdout
    assert "complete -F _tte_completion terminaltexteffects" in result.stdout


def test_bash_completion_suggests_effect_names_and_options() -> None:
    """Bash completion should suggest built-in effects and effect-specific options."""
    result = _run_bash(
        """
eval "$(""" + f"{sys.executable}" + """ -m terminaltexteffects --print-completion bash)"
COMP_WORDS=(tte ma)
COMP_CWORD=1
_tte_completion
printf 'effects:%s\\n' "${COMPREPLY[*]}"
COMP_WORDS=(tte matrix --ra)
COMP_CWORD=2
_tte_completion
printf 'options:%s\\n' "${COMPREPLY[*]}"
""",
    )

    assert "effects:matrix" in result.stdout
    assert "--rain-color-gradient" in result.stdout
    assert "--rain-symbols" in result.stdout


def test_bash_completion_suggests_choice_and_file_values(tmp_path: Path) -> None:
    """Bash completion should offer choice values and file path completions."""
    completion_file = tmp_path / "demo.txt"
    completion_file.write_text("demo", encoding="utf-8")

    result = _run_bash(
        f"""
eval "$({sys.executable} -m terminaltexteffects --print-completion bash)"
COMP_WORDS=(tte --print-completion "")
COMP_CWORD=2
_tte_completion
printf 'shells:%s\\n' "${{COMPREPLY[*]}}"
COMP_WORDS=(tte --input-file "{tmp_path}/d")
COMP_CWORD=2
_tte_completion
printf 'files:%s\\n' "${{COMPREPLY[*]}}"
""",
    )

    assert "shells:bash zsh" in result.stdout
    assert str(completion_file) in result.stdout


def test_bash_completion_includes_plugin_effect_in_clean_shell(tmp_path: Path) -> None:
    """Plugin effects should be available through the full bash completion flow."""
    _write_demo_plugin(tmp_path)

    result = _run_bash(
        """
eval "$(""" + f"{sys.executable}" + """ -m terminaltexteffects --print-completion bash)"
COMP_WORDS=(tte pl)
COMP_CWORD=1
_tte_completion
printf 'effects:%s\\n' "${COMPREPLY[*]}"
COMP_WORDS=(tte plugindemo --pl)
COMP_CWORD=2
_tte_completion
printf 'options:%s\\n' "${COMPREPLY[*]}"
""",
        env={"XDG_CONFIG_HOME": str(tmp_path)},
    )

    assert "effects:plugindemo" in result.stdout
    assert "--plugin-speed" in result.stdout
