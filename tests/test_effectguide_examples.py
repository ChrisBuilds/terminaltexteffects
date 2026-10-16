"""Run every Effect Guide example effect so the guide's code can't drift from the engine API."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools import render_demos

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = PROJECT_ROOT / "docs" / "effectguide" / "examples"
ANSI_ESCAPE = re.compile(r"\x1b(\[[0-?]*[ -/]*[@-~]|[78])")
EXAMPLE_DIRS = sorted(
    path
    for path in EXAMPLES.rglob("*")
    if path.is_dir() and any("def get_effect_resources" in module.read_text() for module in path.glob("*.py"))
)


def test_every_example_has_a_guide_demo() -> None:
    """Each example directory is rendered by `render_demos.py --guide`, so its visual can be regenerated."""
    demo_dirs = {demo.effects_dir for demo in render_demos.GUIDE_DEMOS.values()}
    assert set(EXAMPLE_DIRS) <= demo_dirs


@pytest.mark.parametrize("name", list(render_demos.GUIDE_DEMOS))
def test_guide_demo_runs(name: str, tmp_path: Path) -> None:
    """Each guide demo plays to completion on its documented input and leaves that input on screen."""
    demo = render_demos.GUIDE_DEMOS[name]
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"PYTHONPATH", "PYTHONHOME", "TTE_DEV_EFFECTS_DIR"}
    }
    env |= {"XDG_CONFIG_HOME": str(tmp_path), "PYTHONUTF8": "1"}
    if demo.effects_dir is not None:
        env["TTE_DEV_EFFECTS_DIR"] = str(demo.effects_dir)
    result = subprocess.run(  # noqa: S603 - Runs this checkout's CLI with fixed arguments.
        [
            sys.executable,
            "-m",
            "terminaltexteffects",
            "--input-file",
            str(demo.input_file),
            "--frame-rate",
            "0",
            *demo.tte_args,
            demo.effect,
            *demo.effect_args,
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    final_text = ANSI_ESCAPE.sub("", result.stdout)
    for line in ANSI_ESCAPE.sub("", demo.input_file.read_text(encoding="utf-8")).splitlines():
        assert line in final_text


@pytest.mark.skipif(sys.platform == "win32", reason="the documented script is a POSIX shell script")
def test_color_input_matches_documented_script(tmp_path: Path) -> None:
    """The colored input file is what the script shown in the Color chapter writes."""
    bash = shutil.which("bash")
    assert bash is not None
    subprocess.run(  # noqa: S603 - Runs the documented script with a fixed path.
        [bash, str(EXAMPLES / "color_input.sh")],
        cwd=tmp_path,
        check=True,
        timeout=60,
    )
    assert (tmp_path / "color_input.txt").read_bytes() == (EXAMPLES / "color_input.txt").read_bytes()


def test_documented_myspray_tests_pass(tmp_path: Path) -> None:
    """The tests in tutorial step 7 pass when run as the page says, with the effect's directory on the path."""
    shutil.copy(EXAMPLES / "myspray_tests" / "test_myspray.py", tmp_path)
    env = {key: value for key, value in os.environ.items() if key not in {"PYTHONHOME", "TTE_DEV_EFFECTS_DIR"}}
    env["PYTHONPATH"] = str(EXAMPLES / "myspray_step7")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "test_myspray.py"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "17 passed" in result.stdout


def test_guide_pages_show_rendered_guide_demos() -> None:
    """Pages show only guide demos, every guide demo is shown, and each one has been rendered."""
    pages = (PROJECT_ROOT / "docs" / "effectguide").rglob("*.md")
    shown = {name for page in pages for name in re.findall(r"img/effectguide/(\w+)_demo\.webp", page.read_text())}
    assert shown == set(render_demos.GUIDE_DEMOS)
    for name in shown:
        assert (PROJECT_ROOT / "docs" / "img" / "effectguide" / f"{name}_demo.webp").is_file()


def test_guide_pages_show_rendered_3d_diagrams() -> None:
    """Pages show only known 3D diagrams, every diagram is shown, and each one has been rendered."""
    pytest.importorskip("PIL")
    from tools import render_3d_diagrams  # noqa: PLC0415 - Needs Pillow, which isn't installed on every Python.

    pages = (PROJECT_ROOT / "docs" / "effectguide").rglob("*.md")
    shown = {name for page in pages for name in re.findall(r"img/effectguide/3d/(\w+)\.webp", page.read_text())}
    assert shown == set(render_3d_diagrams.DIAGRAMS)
    for name in shown:
        assert (render_3d_diagrams.OUT_DIR / f"{name}.webp").is_file()


@pytest.mark.skipif(sys.version_info < (3, 13), reason="argparse wraps usage lines differently before 3.13")
@pytest.mark.parametrize("help_file", sorted(EXAMPLES.glob("*/help.txt")), ids=lambda path: path.parent.name)
def test_documented_help_matches(help_file: Path, tmp_path: Path) -> None:
    """Help text shown in the guide is what `tte <effect> -h` prints for that example."""
    env = {key: value for key, value in os.environ.items() if key not in {"PYTHONPATH", "PYTHONHOME"}}
    env |= {"TTE_DEV_EFFECTS_DIR": str(help_file.parent), "XDG_CONFIG_HOME": str(tmp_path), "COLUMNS": "100"}
    module = next(help_file.parent.glob("*.py"))
    command = module.stem
    result = subprocess.run(  # noqa: S603 - Runs this checkout's CLI with fixed arguments.
        [sys.executable, "-m", "terminaltexteffects", command, "-h"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == help_file.read_text(encoding="utf-8")
