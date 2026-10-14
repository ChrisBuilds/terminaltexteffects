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
    """Each guide demo's example effect loads and plays to completion on a small input."""
    demo = render_demos.GUIDE_DEMOS[name]
    assert demo.effects_dir is not None
    env = {key: value for key, value in os.environ.items() if key not in {"PYTHONPATH", "PYTHONHOME"}}
    env |= {"TTE_DEV_EFFECTS_DIR": str(demo.effects_dir), "XDG_CONFIG_HOME": str(tmp_path), "PYTHONUTF8": "1"}
    result = subprocess.run(  # noqa: S603 - Runs this checkout's CLI with fixed arguments.
        [
            sys.executable,
            "-m",
            "terminaltexteffects",
            "--frame-rate",
            "0",
            *demo.tte_args,
            demo.effect,
            *demo.effect_args,
        ],
        input="Hello\nTTE",
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
    assert "Hello" in final_text
    assert "TTE" in final_text
