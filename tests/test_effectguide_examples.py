"""Run every Effect Guide example effect so the guide's code can't drift from the engine API."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tools import render_demos

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = PROJECT_ROOT / "docs" / "effectguide" / "examples"
EXAMPLE_DIRS = sorted(path for path in EXAMPLES.iterdir() if path.is_dir() and any(path.glob("*.py")))


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
    final_text = re.sub(r"\x1b(\[[0-?]*[ -/]*[@-~]|[78])", "", result.stdout)
    for line in demo.input_file.read_text(encoding="utf-8").splitlines():
        assert line in final_text


def test_guide_pages_show_rendered_guide_demos() -> None:
    """Pages show only guide demos, every guide demo is shown, and each one has been rendered."""
    pages = (PROJECT_ROOT / "docs" / "effectguide").rglob("*.md")
    shown = {name for page in pages for name in re.findall(r"img/effectguide/(\w+)_demo\.webp", page.read_text())}
    assert shown == set(render_demos.GUIDE_DEMOS)
    for name in shown:
        assert (PROJECT_ROOT / "docs" / "img" / "effectguide" / f"{name}_demo.webp").is_file()


@pytest.mark.skipif(sys.version_info < (3, 10), reason="argparse names the options section differently before 3.10")
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
