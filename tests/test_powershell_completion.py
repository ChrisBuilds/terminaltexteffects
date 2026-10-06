"""Exercise generated completion in a clean PowerShell 7 session."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from terminaltexteffects import __main__
from terminaltexteffects.utils.shell_completion import get_completion_script
from tools import generate_shell_completions as generator

CASES = {
    "effect": "tte wi",
    "alias": "terminaltexteffects wi",
    "global": "tte --canvas-w",
    "effect-option": "tte wipe --wipe-d",
    "choices": "tte wipe --wipe-direction col",
    "validator": "tte wipe --final-gradient-direction rad",
    "easing": "tte waves --wave-easing in_out_",
    "equals": "tte --print-completion=pow",
    "shell": "tte --print-completion pow",
    "arity": "tte --canvas-width 2 --canvas-height 1 wipe --wipe-d",
    "negative": "tte --canvas-width -1 wipe --wipe-d",
    "flag": "tte --no-color wipe --wipe-d",
    "many-values": "tte --include-effects wipe rain --seed 1 wipe --wipe-d",
    "include": "tte --include-effects wipe ra",
    "many-effect-values": "tte wipe --final-gradient-stops ffffff 000000 --wipe-d",
    "quoted-choice": "tte wipe --wipe-direction 'col",
    "file": "tte --input-file 'demo ",
    "file-equals": "tte --input-file='demo ",
    "file-alias": "tte -i 'demo ",
    "file-unicode": "tte --input-file '界",
    "file-metacharacters": "tte --input-file 'literal",
    "quoted-file-before-effect": "tte --input-file 'demo file.txt' wipe --wipe-d",
    "literal-before-effect": "tte --input-file '$(New-Item injected.txt)' wipe --wipe-d",
    "expression": "tte --input-file $(New-Item injected.txt) wipe --wipe-d",
    "cursor": "tte wi trailing",
    "after-pipeline": "Write-Output OK | tte wi",
    "terminator": "tte -- --can",
}


@pytest.fixture(scope="module")
def completions(tmp_path_factory: pytest.TempPathFactory) -> dict[str, list[str]]:
    """Batch native completion requests without executing the command lines being completed."""
    pwsh = os.environ.get("TTE_PWSH") or shutil.which("pwsh")
    if not pwsh:
        if os.environ.get("TTE_REQUIRE_PWSH") == "1":
            pytest.fail("PowerShell 7 is required in the native-platform CI jobs")
        pytest.skip("PowerShell 7 is not installed")
    directory = tmp_path_factory.mktemp("powershell completion")
    for name in ("demo file.txt", "界 file.txt", "literal$(New-Item injected.txt).txt"):
        (directory / name).write_text("demo", encoding="utf-8")
    (directory / "broken.py").write_text('raise RuntimeError("do not load prototypes")\n', encoding="utf-8")
    plugins = directory / "config" / "terminaltexteffects" / "effects"
    plugins.mkdir(parents=True)
    (plugins / "broken_plugin.py").write_text('raise RuntimeError("do not load plugins")\n', encoding="utf-8")
    env = dict(os.environ, TTE_DEV_EFFECTS_DIR=str(directory), XDG_CONFIG_HOME=str(directory / "config"))
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env["PATH"]
    result = subprocess.run(
        [sys.executable, "-m", "terminaltexteffects", "--print-completion", "powershell"],
        cwd=directory,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    (directory / "completion.ps1").write_text(result.stdout, encoding="utf-8")
    requests = [
        {"name": key, "line": line, "cursor": 6 if key == "cursor" else len(line)} for key, line in CASES.items()
    ]
    (directory / "requests.json").write_text(json.dumps(requests, ensure_ascii=True), encoding="utf-8")
    script = directory / "check.ps1"
    script.write_text(
        "$ErrorActionPreference = 'Stop'\n"
        ". ./completion.ps1\n"
        "$results = @{}\n"
        "foreach ($request in (Get-Content -Raw ./requests.json | ConvertFrom-Json)) {\n"
        "  $completion = [System.Management.Automation.CommandCompletion]::CompleteInput(\n"
        "    $request.line, [int]$request.cursor, $null)\n"
        "  $results[$request.name] = @($completion.CompletionMatches | ForEach-Object CompletionText)\n"
        "}\n"
        "$results | ConvertTo-Json -Depth 5 -Compress\n",
        encoding="utf-8",
    )
    result = subprocess.run(  # noqa: S603 - Fixed test script; requests are literal JSON data.
        [pwsh, "-NoLogo", "-NoProfile", "-NonInteractive", "-File", str(script)],
        cwd=directory,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    assert not (directory / "injected.txt").exists()
    return json.loads(result.stdout)


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("effect", "wipe"),
        ("alias", "wipe"),
        ("global", "--canvas-width"),
        ("effect-option", "--wipe-direction"),
        ("choices", "column_left_to_right"),
        ("validator", "radial"),
        ("easing", "in_out_sine"),
        ("equals", "--print-completion=powershell"),
        ("shell", "powershell"),
        ("arity", "--wipe-direction"),
        ("negative", "--wipe-direction"),
        ("flag", "--wipe-direction"),
        ("many-values", "--wipe-direction"),
        ("include", "rain"),
        ("many-effect-values", "--wipe-direction"),
        ("quoted-choice", "column_left_to_right"),
        ("quoted-file-before-effect", "--wipe-direction"),
        ("literal-before-effect", "--wipe-direction"),
        ("cursor", "wipe"),
        ("after-pipeline", "wipe"),
    ],
)
def test_native_completion_context(completions: dict[str, list[str]], case: str, expected: str) -> None:
    """Both commands complete options and values using argument arity and cursor context."""
    assert expected in completions[case]


@pytest.mark.parametrize("case", ["file", "file-equals", "file-alias", "file-unicode", "file-metacharacters"])
def test_native_file_completion_quotes_paths(completions: dict[str, list[str]], case: str) -> None:
    """File suggestions retain spaces, Unicode, and literal metacharacters with safe quoting."""
    results = completions[case]
    assert results
    assert any("file.txt" in text or "literal" in text for text in results)
    assert all("'" in text for text in results)
    if case == "file-equals":
        assert all(text.startswith("--input-file=") for text in results)


def test_nonliteral_arguments_and_option_terminator(completions: dict[str, list[str]]) -> None:
    """Do not infer effect options past expressions or complete options after the terminator."""
    assert "--wipe-direction" not in completions["expression"]
    assert "--canvas-width" not in completions["terminator"]


def test_metadata_preserves_arity_aliases_and_choices() -> None:
    """Parser-derived data keeps fixed/variable arities and validator choices distinct."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", "-p", nargs=2, choices=("a", "b"))
    parser.add_argument("--many", nargs="*")
    parser.add_argument("--flag", action="store_true")
    root = generator.parser_metadata(parser)["root"]
    assert isinstance(root, dict)
    options = root["options"]
    assert options["--pair"] == options["-p"]
    assert options["--pair"]["min"] == options["--pair"]["max"] == 2
    assert options["--pair"]["choices"] == ["a", "b"]
    assert options["--many"]["min"] == 0
    assert options["--many"]["max"] == -1
    assert options["--flag"]["max"] == 0


def test_powershell_cli_prints_bundled_resource(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Printing the bundled script requires no runtime completion generator dependency."""
    monkeypatch.setattr(sys, "argv", ["tte", "--print-completion", "powershell"])
    __main__.main()
    assert capsys.readouterr().out == get_completion_script("powershell")
