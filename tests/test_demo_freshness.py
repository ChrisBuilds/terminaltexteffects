"""Check that every committed demo still shows what its code records.

`tools/render_demos.py` writes a fingerprint of each demo's recorded frames and render settings to a manifest beside the
demos. This test records each demo again and fails when the fingerprint no longer matches, so a change to an effect, an
example, an input file, the engine or the renderer can't leave a demo showing old behavior.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

from tools import render_demos

if TYPE_CHECKING:
    from pathlib import Path

EFFECT_DEMOS = render_demos.PROJECT_ROOT / "docs" / "img" / "effects_demos"
GUIDE_DEMOS = render_demos.PROJECT_ROOT / "docs" / "img" / "effectguide"

pytestmark = pytest.mark.skipif(
    sys.platform != "linux",
    reason="Demos are rendered and checked on Linux, where floating-point results match CI.",
)


def rerender_command(name: str, out_dir: Path) -> str:
    """Return the command that brings one demo up to date."""
    guide = " --guide" if out_dir == GUIDE_DEMOS else ""
    out = out_dir.relative_to(render_demos.PROJECT_ROOT)
    return f"./.venv/bin/python tools/render_demos.py{guide} {name} --out {out}"


CASES = [
    *((name, demo, EFFECT_DEMOS) for name, demo in render_demos.demos().items()),
    *((name, demo, GUIDE_DEMOS) for name, demo in render_demos.GUIDE_DEMOS.items()),
]


@pytest.mark.parametrize(
    ("out_dir", "demos"), [(EFFECT_DEMOS, render_demos.demos()), (GUIDE_DEMOS, render_demos.GUIDE_DEMOS)]
)
def test_manifest_lists_exactly_the_demos(out_dir: Path, demos: dict[str, render_demos.Demo]) -> None:
    """Every demo has a fingerprint, and no fingerprint is left from a removed demo."""
    assert set(render_demos.read_manifest(out_dir)) == set(demos)


@pytest.mark.parametrize(("name", "demo", "out_dir"), CASES, ids=[f"{out.name}/{name}" for name, _, out in CASES])
def test_demo_matches_its_code(name: str, demo: render_demos.Demo, out_dir: Path, tmp_path: Path) -> None:
    """The demo records the same frames it was rendered from."""
    recording = tmp_path / "demo.tterec"
    render_demos.record_for_render(demo, recording)
    expected = render_demos.read_manifest(out_dir).get(name)
    actual = render_demos.fingerprint(recording, demo, render_demos.DEFAULT_FPS)
    assert actual == expected, f"{name} is out of date with its code. Re-render it: {rerender_command(name, out_dir)}"
