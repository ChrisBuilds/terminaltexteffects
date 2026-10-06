"""Execute a small set of actual documented examples; do not copy their code into tests."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def example(source: str, identifier: str, language: str) -> str:
    """Select one explicit marker followed immediately by a standalone fenced code block."""
    marker = f"<!-- tte-example: {identifier} -->"
    if source.count(marker) != 1:
        message = f"Expected exactly one documentation marker {marker}"
        raise ValueError(message)
    selected = source.split(marker, 1)[1].lstrip("\n")
    match = re.match(rf"```{re.escape(language)}\n(.*?)\n```(?:\n|$)", selected, re.DOTALL)
    if match is None:
        message = f"Expected a complete {language} fence immediately after {marker}"
        raise ValueError(message)
    return match.group(1) + "\n"


def environment(outside: Path) -> dict[str, str]:
    """Use this installation and an empty config directory instead of personal prototypes/profiles."""
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"PYTHONPATH", "PYTHONHOME", "TTE_DEV_EFFECTS_DIR", "BASH_ENV", "ENV"}
    }
    env["XDG_CONFIG_HOME"] = str(outside / "empty-config")
    env["PYTHONUTF8"] = "1"
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    return env


def rendered_text(output: str) -> str:
    """Remove CSI formatting/cursor sequences for semantic text assertions."""
    return re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", output).strip()


def test_library_example(tmp_path: Path) -> None:
    """Run the exact documented library example outside the checkout with a bounded timeout."""
    script = example((PROJECT_ROOT / "docs/libguide.md").read_text(encoding="utf-8"), "library-wipe", "python")
    result = subprocess.run(  # noqa: S603 - Run the explicitly selected repository example, no shell.
        [sys.executable, "-I", "-c", script],
        cwd=tmp_path,
        env=environment(tmp_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert rendered_text(result.stdout) == "Hi", result.stdout


def test_cli_example(tmp_path: Path) -> None:
    """Exercise documented piping, global/effect arguments, output, and terminal restoration."""
    bash = shutil.which("bash")
    if bash is None:
        if os.environ.get("TTE_REQUIRE_DOC_EXAMPLES") == "1":
            pytest.fail("Code quality requires Bash for the documented CLI example")
        pytest.skip("Documented POSIX CLI example requires Bash")
    script = example((PROJECT_ROOT / "docs/appguide.md").read_text(encoding="utf-8"), "cli-wipe", "bash")
    env = environment(tmp_path)
    entry = shutil.which("tte", path=env["PATH"])
    assert entry is not None
    assert Path(entry).parent.resolve() == Path(sys.executable).parent.resolve()
    result = subprocess.run(  # noqa: S603 - Intentional execution of the explicit Bash documentation example.
        [bash, "--noprofile", "--norc", "-o", "pipefail", "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert rendered_text(result.stdout).endswith("Hi"), result.stdout
    assert "\x1b[?25l" in result.stdout
    assert "\x1b[?25h" in result.stdout


@pytest.mark.parametrize(
    "source",
    [
        "```python\nprint('unmarked')\n```\n",
        "<!-- tte-example: demo -->\n<!-- tte-example: demo -->\n",
        "<!-- tte-example: demo -->\n```bash\necho wrong-language\n```\n",
        "<!-- tte-example: demo -->\n```python\nprint('unterminated')\n",
    ],
)
def test_invalid_example_selection_fails(source: str) -> None:
    """Missing/duplicate markers and bad fences fail rather than execute unrelated prose."""
    with pytest.raises(ValueError, match="Expected"):
        example(source, "demo", "python")


def test_selection_does_not_include_adjacent_blocks() -> None:
    """Unselected examples and explanatory text must not be executed."""
    source = "```python\nfirst()\n```\n<!-- tte-example: demo -->\n```python\nselected()\n```\n```python\nlast()\n```\n"
    assert example(source, "demo", "python") == "selected()\n"
