"""CLI tests for completion generation and parser wiring."""

from __future__ import annotations

import argparse
import importlib
import os
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from terminaltexteffects import __main__
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.shell_completion import get_completion_script

if TYPE_CHECKING:
    from pathlib import Path
    from pkgutil import ModuleInfo

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


def test_bundled_parser_does_not_import_local_development_effect(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bundled parser generation excludes the gitignored local development module."""
    original_iter_modules = __main__.pkgutil.iter_modules
    original_import_module = __main__.importlib.import_module
    dev_name = "terminaltexteffects.effects.effect_dev"

    def iter_modules(path: list[str] | None = None, prefix: str = "") -> list[ModuleInfo]:
        modules = list(original_iter_modules(path, prefix))
        modules.append(
            __main__.pkgutil.ModuleInfo(module_finder=modules[0].module_finder, name=dev_name, ispkg=False),
        )
        return modules

    def import_module(name: str) -> object:
        assert name != dev_name
        return original_import_module(name)

    monkeypatch.setattr(__main__.pkgutil, "iter_modules", iter_modules)
    monkeypatch.setattr(__main__.importlib, "import_module", import_module)
    _, effects = __main__.build_parser(include_user_effects=False)

    assert "dev" not in effects
    assert "matrix" in effects


def test_wipe_help_renders_direction_default_as_cli_value() -> None:
    """Ensure wipe help presents its enum default in command-line syntax."""
    parser, _ = __main__.build_parser()
    subparsers = next(action for action in parser._actions if action.dest == "effect")
    assert isinstance(subparsers, argparse._SubParsersAction)

    help_output = subparsers.choices["wipe"].format_help()

    assert "(default:\n                        diagonal_top_left_to_bottom_right)" in help_output
    assert "CharacterGroup.DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT" not in help_output
    assert all(direction in help_output for direction in argutils.CharacterGroupArg.METAVAR)


def test_laseretch_help_renders_color_defaults_as_cli_values() -> None:
    """Ensure multi-color defaults are displayed as CLI tokens rather than Python objects."""
    parser, _ = __main__.build_parser()
    subparsers = next(action for action in parser._actions if action.dest == "effect")
    assert isinstance(subparsers, argparse._SubParsersAction)

    help_output = subparsers.choices["laseretch"].format_help()

    assert "(default: ffe680 ff7b00)" in help_output
    assert "Color('ffe680')" not in help_output


def test_main_print_completion_bash_outputs_script(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Printing bash completion should not require stdin or an effect."""
    monkeypatch.setattr(__main__.sys, "argv", ["tte", "--print-completion", "bash"])

    __main__.main()

    output = capsys.readouterr().out
    assert "complete -o filenames -F _shtab_tte tte" in output
    assert "complete -o filenames -F _shtab_tte terminaltexteffects" in output
    assert "mapfile" not in output
    assert "--wrap-text" in output
    assert "--random-effect" in output
    assert "--include-effects" in output
    assert "matrix" in output
    assert "laseretch" in output
    assert "highlight" in output
    assert "--highlight-brightness" in output
    assert "--rain-color-gradient" in output


def test_main_print_completion_without_shell_outputs_setup_commands(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Printing completion without a shell should provide copy-and-paste setup commands."""
    monkeypatch.setattr(__main__.sys, "argv", ["tte", "--print-completion"])

    __main__.main()

    assert capsys.readouterr().out == (
        "Enable completions in the current shell:\n"
        '  Bash: eval "$(tte --print-completion bash)"\n'
        '  Zsh:  eval "$(tte --print-completion zsh)"\n'
        "  PowerShell 7+: tte --print-completion powershell | Out-String | Invoke-Expression\n"
    )


def test_main_print_completion_zsh_outputs_script(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Printing zsh completion should emit a native zsh script."""
    monkeypatch.setattr(__main__.sys, "argv", ["tte", "--print-completion", "zsh"])

    __main__.main()

    output = capsys.readouterr().out
    assert output.startswith("#compdef tte terminaltexteffects")
    assert "_arguments" in output
    assert "compdef _shtab_tte -N tte terminaltexteffects" in output
    direction_spec = next(
        line for line in output.splitlines() if line.lstrip().startswith('"--final-gradient-direction[')
    )
    assert direction_spec.endswith(':(diagonal horizontal vertical radial)"')
    easing_spec = next(line for line in output.splitlines() if line.lstrip().startswith('"--wipe-ease['))
    assert ":(linear in_sine" in easing_spec
    assert "in_out_bounce)" in output
    assert "bashcompinit" not in output


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


@pytest.mark.parametrize("input_data", ["", " \t\n"])
def test_main_empty_input_is_silent_success(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    input_data: str,
) -> None:
    """Empty and whitespace-only input should exit before rendering without output."""
    monkeypatch.setattr(__main__.sys, "argv", ["tte", "rain"])
    monkeypatch.setattr(__main__.Terminal, "get_piped_input", lambda: input_data)

    __main__.main()

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


@pytest.mark.parametrize(
    ("arguments", "input_data"),
    [
        pytest.param(["tte", "rain"], "\x1b[0m", id="ansi-only-input"),
        pytest.param(["tte", "--canvas-width", "1", "rain"], "   X", id="fully-clipped-input"),
    ],
)
def test_main_empty_renderable_input_exits_with_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    arguments: list[str],
    input_data: str,
) -> None:
    """Input without visible characters should fail before effect construction."""
    monkeypatch.setattr(__main__.sys, "argv", arguments)
    monkeypatch.setattr(__main__.Terminal, "get_piped_input", lambda: input_data)

    with pytest.raises(SystemExit) as exc_info:
        __main__.main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Input contains no visible characters" in captured.err


def test_runtime_parser_includes_plugin_effect(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Normal runtime parser construction should continue to discover plugins."""
    _write_demo_plugin(tmp_path)

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    _, effect_resource_map = __main__.build_parser()

    assert "plugindemo" in effect_resource_map


def _write_plugin(tmp_path: Path, filename: str, source: str) -> Path:
    """Write a user effect plugin into the temporary XDG config directory and return its path."""
    plugin_dir = tmp_path / "terminaltexteffects" / "effects"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    plugin_file = plugin_dir / filename
    plugin_file.write_text(source.strip() + "\n", encoding="utf-8")
    return plugin_file


def _plugin_config_source(command: str, effect_cmd: str | None = None, options: str = "") -> str:
    """Return plugin source whose config parser command is `command`."""
    return f"""
from dataclasses import dataclass

from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.utils import argutils


class PluginEffect:
    pass


@dataclass
class PluginConfig(BaseConfig):
    parser_spec: argutils.ParserSpec = argutils.ParserSpec(
        name={command!r},
        help="plugin help",
        description="plugin description",
        epilog="plugin epilog",
    )
{options}


def get_effect_resources():
    return {effect_cmd or command!r}, PluginEffect, PluginConfig
"""


def test_runtime_parser_skips_plugin_that_fails_to_import(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A user plugin that cannot be imported is skipped without hiding other effects."""
    _write_demo_plugin(tmp_path)
    broken_plugin = _write_plugin(tmp_path, "broken.py", "def broken(:")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    parser, effect_resource_map = __main__.build_parser()

    assert "wipe" in effect_resource_map
    assert parser.parse_args(["plugindemo", "--plugin-speed", "7"]).plugin_speed == 7
    warning = capsys.readouterr().err
    assert f"Warning: Skipping user effect plugin '{broken_plugin}': SyntaxError" in warning
    assert "_tte_user_broken" not in sys.modules


@pytest.mark.parametrize(
    ("source", "expected_warning"),
    [
        pytest.param("import sys\nsys.exit(3)", "SystemExit: 3", id="system-exit"),
        pytest.param("raise RuntimeError('import failed')", "RuntimeError: import failed", id="import-error"),
        pytest.param(
            "def get_effect_resources():\n    return 'invalid', object",
            "TypeError: get_effect_resources() must return",
            id="wrong-shape",
        ),
        pytest.param(
            "def get_effect_resources():\n    return '', object, object",
            "ValueError: Effect command must be a non-empty string",
            id="empty-command",
        ),
        pytest.param(
            "def get_effect_resources():\n    return 'invalid', 'effect', 'config'",
            "TypeError: Effect and config resources must be classes",
            id="not-classes",
        ),
        pytest.param(
            _plugin_config_source("wipe"),
            "ValueError: Duplicate effect command detected: wipe",
            id="duplicate-builtin",
        ),
        pytest.param(
            _plugin_config_source("invalid", effect_cmd="other"),
            "ValueError: Effect command 'other' does not match parser command 'invalid'",
            id="mismatched-command",
        ),
        pytest.param(
            _plugin_config_source(
                "invalid",
                options=(
                    "    first: int = argutils.ArgSpec(name='--same', default=1, type=int)\n"
                    "    second: int = argutils.ArgSpec(name='--same', default=2, type=int)"
                ),
            ),
            "ArgumentError",
            id="conflicting-options",
        ),
    ],
)
def test_runtime_parser_skips_plugin_that_fails_to_register(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    source: str,
    expected_warning: str,
) -> None:
    """A failed user plugin leaves no partial command and keeps built-in effects available."""
    broken_plugin = _write_plugin(tmp_path, "broken.py", source)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    parser, effect_resource_map = __main__.build_parser()

    assert "wipe" in effect_resource_map
    assert "invalid" not in effect_resource_map
    assert "other" not in effect_resource_map
    with pytest.raises(SystemExit):
        parser.parse_args(["invalid"])
    warning = capsys.readouterr().err
    assert f"Warning: Skipping user effect plugin '{broken_plugin}': {expected_warning}" in warning
    assert "_tte_user_broken" not in sys.modules


def test_runtime_parser_loads_plugin_module_without_effect_resources(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A user module without `get_effect_resources()` is imported without a warning or command."""
    _write_plugin(tmp_path, "helpers.py", "HELPER = True")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    _, effect_resource_map = __main__.build_parser(include_user_effects=False)
    builtin_effects = set(effect_resource_map)
    _, effect_resource_map = __main__.build_parser()

    assert set(effect_resource_map) == builtin_effects
    assert capsys.readouterr().err == ""
    assert sys.modules["_tte_user_helpers"].HELPER is True


def test_runtime_parser_propagates_keyboard_interrupt_from_plugin(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Interrupting plugin discovery still stops the CLI."""
    _write_plugin(tmp_path, "interrupt.py", "raise KeyboardInterrupt")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    with pytest.raises(KeyboardInterrupt):
        __main__.build_parser()

    assert "_tte_user_interrupt" not in sys.modules


def test_user_plugin_module_name_does_not_shadow_installed_modules(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A plugin file named like an installed module is imported under a private module name."""
    import random  # noqa: PLC0415

    _write_plugin(tmp_path, "random.py", _plugin_config_source("randomplugin"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    _, effect_resource_map = __main__.build_parser()

    assert "randomplugin" in effect_resource_map
    assert sys.modules["random"] is random
    assert effect_resource_map["randomplugin"][0].__module__ == "_tte_user_random"


def test_bundled_completion_does_not_import_plugin_effect(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Printing bundled completion should not import user effect modules."""
    plugin_dir = tmp_path / "terminaltexteffects" / "effects"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "broken_plugin.py").write_text("raise RuntimeError('plugin imported')", encoding="utf-8")

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(__main__.sys, "argv", ["tte", "--print-completion", "bash"])

    __main__.main()

    output = capsys.readouterr().out
    assert "complete -o filenames -F _shtab_tte tte" in output


def test_bash_completion_registers_in_clean_shell() -> None:
    """The bash completion script should register both CLI entry points."""
    result = _run_bash(
        'eval "$('
        f"{sys.executable} -m terminaltexteffects --print-completion bash"
        ')"; complete -p tte; complete -p terminaltexteffects',
    )

    assert "complete -o filenames -F _shtab_tte tte" in result.stdout
    assert "complete -o filenames -F _shtab_tte terminaltexteffects" in result.stdout


def test_zsh_completion_registers_in_clean_shell() -> None:
    """The native zsh completion script should self-bootstrap in a clean shell."""
    result = _run_zsh(
        'eval "$('
        f"{sys.executable} -m terminaltexteffects --print-completion zsh"
        ')"; whence -w _shtab_tte; print -r -- "tte:${_comps[tte]} terminaltexteffects:${_comps[terminaltexteffects]}"',
    )

    assert "_shtab_tte: function" in result.stdout
    assert "tte:_shtab_tte terminaltexteffects:_shtab_tte" in result.stdout


def test_zsh_completion_ignores_insecure_directories(tmp_path: Path) -> None:
    """Completion initialization skips insecure search paths without prompting for terminal input."""
    completion_dir = tmp_path / "insecure-completions"
    completion_dir.mkdir()
    (completion_dir / "_tte_untrusted").write_text("#compdef tte_untrusted\n", encoding="utf-8")
    completion_dir.chmod(0o777)  # Reproduce Zsh's insecure-directory audit failure.
    zsh_state_dir = tmp_path / "zsh-state"
    zsh_state_dir.mkdir()
    result = _run_zsh(
        'fpath=("$TTE_TEST_COMPLETION_DIR" $fpath); eval "$('
        f"{sys.executable} -m terminaltexteffects --print-completion zsh"
        ')"; print -r -- "tte:${_comps[tte]} terminaltexteffects:${_comps[terminaltexteffects]}"; '
        'print -r -- "untrusted:${_comps[tte_untrusted]}"',
        env={"TTE_TEST_COMPLETION_DIR": str(completion_dir), "ZDOTDIR": str(zsh_state_dir)},
    )

    assert "tte:_shtab_tte terminaltexteffects:_shtab_tte" in result.stdout
    assert "untrusted:\n" in result.stdout
    assert "initialization aborted" not in result.stderr
    assert "can't open terminal" not in result.stderr


def test_bash_completion_suggests_effect_names_and_options() -> None:
    """Bash completion should suggest built-in effects and effect-specific options."""
    result = _run_bash(
        """
eval "$("""
        f"{sys.executable}"
        """ -m terminaltexteffects --print-completion bash)"
COMP_WORDS=(tte ma)
COMP_CWORD=1
_shtab_tte
printf 'effects:%s\\n' "${COMPREPLY[*]}"
COMP_WORDS=(tte matrix --ra)
COMP_CWORD=2
_shtab_tte
printf 'options:%s\\n' "${COMPREPLY[*]}"
""",
    )

    assert "effects:matrix" in result.stdout
    assert "--rain-color-gradient" in result.stdout
    assert "--rain-symbols" in result.stdout


def test_bash_completion_suggests_custom_validator_values() -> None:
    """Bash completion should expose enum-like and easing values from custom validators."""
    result = _run_bash(
        """
eval "$("""
        f"{sys.executable}"
        """ -m terminaltexteffects --print-completion bash)"
COMP_WORDS=(tte beams --final-gradient-direction "")
COMP_CWORD=3
_shtab_tte
printf 'directions:%s\\n' "${COMPREPLY[*]}"
COMP_WORDS=(tte wipe --wipe-direction diagonal_)
COMP_CWORD=3
_shtab_tte
printf 'groups:%s\\n' "${COMPREPLY[*]}"
COMP_WORDS=(tte wipe --wipe-ease in_out_b)
COMP_CWORD=3
_shtab_tte
printf 'easing:%s\\n' "${COMPREPLY[*]}"
""",
    )

    assert "directions:diagonal horizontal vertical radial" in result.stdout
    assert "diagonal_top_left_to_bottom_right" in result.stdout
    assert "diagonal_bottom_right_to_top_left" in result.stdout
    assert "easing:in_out_back in_out_bounce" in result.stdout


@pytest.mark.parametrize(
    ("command", "option"),
    [
        ("wipe", "--wipe-direction"),
        ("highlight", "--highlight-direction"),
        ("sweep", "--first-sweep-direction"),
        ("sweep", "--second-sweep-direction"),
        ("laseretch", "--etch-pattern"),
        ("waves", "--wave-direction"),
    ],
)
def test_completion_suggests_all_supported_groupings(command: str, option: str) -> None:
    """Bundled Bash and Zsh choices cover every grouping and are accepted by the runtime parser."""
    result = _run_bash(
        f"""
eval "$({sys.executable} -m terminaltexteffects --print-completion bash)"
COMP_WORDS=(tte {command} {option} "")
COMP_CWORD=3
_shtab_tte
printf '%s\\n' "${{COMPREPLY[@]}}"
""",
    )
    expected = argutils.CharacterGroupArg.COMPLETION_CHOICES
    if command == "laseretch":
        expected = ("algorithm", *argutils.CharacterOrderArg.COMPLETION_CHOICES)
    elif command in ("wipe", "highlight", "sweep", "waves"):
        expected = argutils.CharacterOrderArg.COMPLETION_CHOICES
    assert set(result.stdout.splitlines()) == set(expected)
    zsh_spec = next(
        line for line in get_completion_script("zsh").splitlines() if line.lstrip().startswith(f'"{option}[')
    )
    assert zsh_spec.endswith(f':({" ".join(expected)})"')

    parser, _ = __main__.build_parser(include_user_effects=False)
    for choice in expected:
        parser.parse_args([command, option, choice])


@pytest.mark.parametrize("prefix", ["circle_", "diamonds_"])
def test_waves_completion_suggests_radial_directions(prefix: str) -> None:
    """Waves advertises both directions for diamond and circular bands."""
    result = _run_bash(
        f"""
eval "$({sys.executable} -m terminaltexteffects --print-completion bash)"
COMP_WORDS=(tte waves --wave-direction {prefix})
COMP_CWORD=3
_shtab_tte
printf '%s\\n' "${{COMPREPLY[@]}}"
""",
    )
    expected = {f"{prefix}center_to_outside", f"{prefix}outside_to_center"}
    assert set(result.stdout.splitlines()) == expected
    zsh_completion = get_completion_script("zsh")
    assert (
        "diamonds_center_to_outside diamonds_outside_to_center circle_center_to_outside circle_outside_to_center "
        in zsh_completion
    )
    parser, _ = __main__.build_parser(include_user_effects=False)
    for direction in expected:
        parsed = parser.parse_args(["waves", "--wave-direction", direction])
        assert parsed.wave_direction is argutils.CharacterOrder[direction.upper()]


@pytest.mark.parametrize(
    ("command", "flags"),
    [
        ("wipe", ["--reverse-wipe-direction"]),
        ("highlight", ["--reverse-highlight-direction"]),
        ("waves", ["--reverse-wave-direction"]),
        ("laseretch", ["--reverse-etch-pattern"]),
        ("sweep", ["--reverse-first-sweep-direction", "--reverse-second-sweep-direction"]),
    ],
)
def test_character_order_reverse_flags_parse_and_complete(command: str, flags: list[str]) -> None:
    """Both shells suggest the actual boolean flags, which default to False and accept CLI activation."""
    result = _run_bash(
        f"""
eval "$({sys.executable} -m terminaltexteffects --print-completion bash)"
COMP_WORDS=(tte {command} --reverse-)
COMP_CWORD=2
_shtab_tte
printf '%s\\n' "${{COMPREPLY[@]}}"
""",
    )
    assert set(result.stdout.splitlines()) == set(flags)
    parser, _ = __main__.build_parser(include_user_effects=False)
    defaults = parser.parse_args([command])
    enabled = parser.parse_args([command, *flags])
    zsh_completion = get_completion_script("zsh")
    for flag in flags:
        field = flag.removeprefix("--").replace("-", "_")
        assert getattr(defaults, field) is False
        assert getattr(enabled, field) is True
        assert f'"{flag}[' in zsh_completion


@pytest.mark.parametrize("command", ["waves", "sweep"])
def test_travel_speed_option_completes_in_bash_and_zsh(command: str) -> None:
    """Both bundled shells advertise the effects' travel-speed arguments."""
    result = _run_bash(
        f"""
eval "$({sys.executable} -m terminaltexteffects --print-completion bash)"
COMP_WORDS=(tte {command} --travel-)
COMP_CWORD=2
_shtab_tte
printf '%s\\n' "${{COMPREPLY[@]}}"
""",
    )
    assert result.stdout.splitlines() == ["--travel-speed"]
    assert '"--travel-speed[' in get_completion_script("zsh")


def test_bash_completion_suggests_choice_and_file_values(tmp_path: Path) -> None:
    """Bash completion should offer choice values and file path completions."""
    completion_file = tmp_path / "demo file.txt"
    completion_file.write_text("demo", encoding="utf-8")

    result = _run_bash(
        f"""
eval "$({sys.executable} -m terminaltexteffects --print-completion bash)"
COMP_WORDS=(tte --print-completion "")
COMP_CWORD=2
_shtab_tte
printf 'shells:%s\\n' "${{COMPREPLY[*]}}"
COMP_WORDS=(tte --input-file "{tmp_path}/d")
COMP_CWORD=2
_shtab_tte
printf 'files:%s\\n' "${{COMPREPLY[*]}}"
COMP_WORDS=(tte --include-effects ma)
COMP_CWORD=2
_shtab_tte
printf 'included:%s\\n' "${{COMPREPLY[*]}}"
""",
    )

    assert "shells:bash zsh powershell" in result.stdout
    assert str(completion_file) in result.stdout
    assert "included:matrix" in result.stdout


def test_bash_completion_excludes_plugin_effect_in_clean_shell(tmp_path: Path) -> None:
    """Bundled completion should not change when a user plugin is installed."""
    _write_demo_plugin(tmp_path)

    result = _run_bash(
        """
eval "$("""
        f"{sys.executable}"
        """ -m terminaltexteffects --print-completion bash)"
COMP_WORDS=(tte pl)
COMP_CWORD=1
_shtab_tte
printf 'effects:%s\\n' "${COMPREPLY[*]}"
COMP_WORDS=(tte plugindemo --pl)
COMP_CWORD=2
_shtab_tte
printf 'options:%s\\n' "${COMPREPLY[*]}"
""",
        env={"XDG_CONFIG_HOME": str(tmp_path)},
    )

    assert "effects:" in result.stdout
    assert "plugindemo" not in result.stdout
    assert "--plugin-speed" not in result.stdout


def test_bundled_completion_scripts_are_current() -> None:
    """Committed completion resources should match the built-in parser."""
    pytest.importorskip("shtab")
    generator = importlib.import_module("tools.generate_shell_completions")

    assert generator.write_completion_scripts(check=True)


@pytest.mark.parametrize("include_external", [True, False])
def test_development_effects_require_explicit_opt_in(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    include_external: bool,
) -> None:
    """The shared parser exposes selected prototypes while bundled discovery excludes them."""
    _write_demo_plugin(tmp_path)
    directory = tmp_path / "terminaltexteffects" / "effects"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty-config"))
    monkeypatch.delenv("TTE_DEV_EFFECTS_DIR", raising=False)
    assert "plugindemo" not in __main__.build_parser()[1]
    monkeypatch.setenv("TTE_DEV_EFFECTS_DIR", str(directory))
    parser, effects = __main__.build_parser(include_user_effects=include_external)
    assert ("plugindemo" in effects) is include_external
    if include_external:
        assert parser.parse_args(["plugindemo", "--plugin-speed", "7"]).plugin_speed == 7


def test_builtin_discovery_does_not_execute_development_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Completion generation remains independent of broken unfinished effects."""
    (tmp_path / "effect_unfinished.py").write_text('raise RuntimeError("unfinished")\n')
    monkeypatch.setenv("TTE_DEV_EFFECTS_DIR", str(tmp_path))
    assert "wipe" in __main__.build_parser(include_user_effects=False)[1]
    with pytest.raises(RuntimeError, match="unfinished"):
        __main__.build_parser()


@pytest.mark.parametrize("directory", ["", "missing-directory"])
def test_development_directory_must_exist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    directory: str,
) -> None:
    """A mistaken opt-in path fails clearly instead of silently hiding prototypes."""
    monkeypatch.setenv("TTE_DEV_EFFECTS_DIR", str(tmp_path / directory) if directory else "")
    with pytest.raises(ValueError, match="must name an existing directory"):
        __main__.build_parser()


def test_development_effect_cannot_shadow_a_builtin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Development effects use the same duplicate-command protection as other effects."""
    _write_demo_plugin(tmp_path)
    directory = tmp_path / "terminaltexteffects" / "effects"
    plugin = directory / "plugin_demo.py"
    plugin.write_text(plugin.read_text().replace("plugindemo", "wipe"))
    monkeypatch.setenv("TTE_DEV_EFFECTS_DIR", str(directory))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty-config"))
    with pytest.raises(ValueError, match="Duplicate effect command detected: wipe"):
        __main__.build_parser()


def test_development_effect_runs_from_installed_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A real prototype uses the normal CLI execution path and effect options."""
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
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "terminaltexteffects",
            "--seed",
            "94",
            "--frame-rate",
            "0",
            "--no-color",
            "--canvas-width",
            "2",
            "--canvas-height",
            "1",
            "--ignore-terminal-dimensions",
            "prototype",
            "--final-gradient-stops",
            "ffffff",
            "--final-gradient-steps",
            "1",
            "--final-gradient-frames",
            "1",
        ],
        cwd=tmp_path,
        input="OK",
        text=True,
        capture_output=True,
        check=True,
    )
    assert "OK" in result.stdout


def test_development_launcher_selects_checkout_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    """The launcher selects this checkout and forwards arguments to the ordinary CLI."""
    from tools import dev  # noqa: PLC0415 - Only this launcher test imports development tooling.

    monkeypatch.setenv("TTE_DEV_EFFECTS_DIR", "some-other-checkout")
    monkeypatch.setattr(sys, "argv", ["tools.dev", "prototype", "--help"])
    calls: list[list[str]] = []
    monkeypatch.setattr(dev, "main", lambda: calls.append(sys.argv.copy()))
    dev.run()
    assert os.environ["TTE_DEV_EFFECTS_DIR"] == str(__main__.Path(dev.__file__).resolve().parents[1] / "dev_effects")
    assert calls == [["tools.dev", "prototype", "--help"]]


@pytest.mark.parametrize("shell", ["bash", "powershell"])
@pytest.mark.parametrize("option", ["--print-completion", "--print-c"])
@pytest.mark.parametrize("equals_form", [False, True])
def test_completion_requests_skip_broken_prototypes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    shell: str,
    option: str,
    *,
    equals_form: bool,
) -> None:
    """Full and abbreviated argparse option forms avoid executing unfinished development code."""
    (tmp_path / "broken.py").write_text('raise RuntimeError("unfinished prototype")\n')
    monkeypatch.setenv("TTE_DEV_EFFECTS_DIR", str(tmp_path))
    completion_args = [f"{option}={shell}"] if equals_form else [option, shell]
    monkeypatch.setattr(sys, "argv", ["tte", *completion_args])
    args, effects = __main__.build_parsers_and_parse_args()
    assert args.print_completion == shell
    assert "wipe" in effects


@pytest.mark.parametrize("effect_option", ["--print", "--p"])
def test_prototype_options_do_not_disable_discovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    effect_option: str,
) -> None:
    """Completion-like effect options remain scoped to their subcommand."""
    _write_demo_plugin(tmp_path)
    directory = tmp_path / "terminaltexteffects" / "effects"
    plugin = directory / "plugin_demo.py"
    plugin.write_text(plugin.read_text().replace("--plugin-speed", "--print"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty-config"))
    monkeypatch.setenv("TTE_DEV_EFFECTS_DIR", str(directory))
    monkeypatch.setattr(sys, "argv", ["tte", "--seed", "94", "plugindemo", effect_option, "2"])
    args, effects = __main__.build_parsers_and_parse_args()
    assert args.print == 2
    assert "plugindemo" in effects
