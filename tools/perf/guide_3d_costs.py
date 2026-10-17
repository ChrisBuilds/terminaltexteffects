"""Measure the frame costs quoted in the Effect Guide's 3D Performance chapter.

Each guide example runs on the concept input on an 80 by 24 canvas with the frame-rate limit off, and the median of
several runs is reported as milliseconds per frame. The sphere and mounted-character tables time `Space3D.step()`
alone. The output is Markdown with the revision, Python version and processor it was measured on.

Run it from the repository root:

    ./.venv/bin/python -m tools.perf.guide_3d_costs
"""

from __future__ import annotations

import argparse
import os
import platform
import statistics
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING

from terminaltexteffects import __main__ as tte_main
from terminaltexteffects.engine.space3d import Shaded, Space3D, Sphere, Textured
from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from tools.perf.benchmark_effects import build_configs, run_iteration

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from terminaltexteffects.engine.space3d import Look

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = PROJECT_ROOT / "docs" / "effectguide" / "examples"
CONCEPT_INPUT = (EXAMPLES / "concept_input.txt").read_text(encoding="utf-8")
CANVAS_ARGS = ("--canvas-width", "80", "--canvas-height", "24", "--anchor-text", "c")

EXAMPLE_ROWS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("wireframes", "wireframes", ()),
    ("card", "card", ()),
    ("cubes", "cubes", ()),
    ("logo", "logo", ()),
    ("depth", "depth", ()),
    ("depth", "depth", ("--see-through",)),
    ("light", "light", ()),
    ("light", "light", ("--shape", "torus")),
    ("gallery", "gallery", ()),
    ("texture", "texture", ("--text",)),
    ("globe", "globe", ()),
)
"""Example directory, command and arguments for each row of the example table."""

SPHERE_ROWS: tuple[tuple[int, int, Callable[[], Look]], ...] = (
    (8, 4, Shaded),
    (16, 8, Shaded),
    (24, 12, Shaded),
    (32, 16, Shaded),
    (48, 24, Shaded),
    (24, 12, lambda: Textured(back="dim")),
    (48, 24, Textured),
    (48, 24, lambda: Textured(back="dim")),
)
"""Segments, rings and look for each row of the sphere table."""


def time_example(directory: str, command: str, args: Sequence[str], samples: int) -> tuple[float, int]:
    """Return the median milliseconds per frame of a guide example, and its frame count."""
    os.environ["TTE_DEV_EFFECTS_DIR"] = str(EXAMPLES / "3d" / directory)
    effect_config, terminal_config = build_configs(command, args, CANVAS_ARGS)
    _, resources = tte_main.build_parser()
    effect_class, _ = resources[command]
    results = [
        run_iteration(
            effect_class, CONCEPT_INPUT, seed=1337, effect_config=effect_config, terminal_config=terminal_config
        )
        for _ in range(samples)
    ]
    frames = results[0].frames
    return statistics.median(result.render_seconds for result in results) * 1000 / frames, frames


def make_terminal(text: str, width: int = 80, height: int = 24) -> Terminal:
    """Return a terminal with a fixed canvas, as the examples use."""
    config = TerminalConfig._build_config()
    config.frame_rate = 0
    config.canvas_width, config.canvas_height = width, height
    return Terminal(text, config=config)


def time_steps(space: Space3D, steps: int, samples: int) -> float:
    """Return the median milliseconds per `space.step()` over `steps` steps, `samples` times."""
    times = []
    for _ in range(samples):
        start = time.perf_counter()
        for _ in range(steps):
            space.step()
        times.append((time.perf_counter() - start) * 1000 / steps)
    return statistics.median(times)


def time_sphere(segments: int, rings: int, look: Look, samples: int) -> float:
    """Return the median milliseconds per step of a turning sphere of radius 20."""
    space = Space3D(make_terminal(CONCEPT_INPUT))
    space.body(Sphere(radius=20, segments=segments, rings=rings)).draw(look).spin("y", turns=100, frames=100_000)
    return time_steps(space, 60, samples)


def time_mounts(text: str, width: int, height: int, samples: int) -> tuple[float, int]:
    """Return the median milliseconds per step with every visible character mounted on a turning plane."""
    terminal = make_terminal(text, width, height)
    space = Space3D(terminal)
    characters = [character for character in terminal.get_characters() if character.input_symbol != " "]
    plane = space.body()
    plane.add_chars(characters, plane.text_plane(characters))
    plane.spin("y", turns=100, frames=100_000)
    return time_steps(space, 60, samples), len(characters)


def environment() -> str:
    """Return the revision, Python version and processor, for the record."""
    revision = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607 - Git from PATH, as in the rest of tools/.
        capture_output=True,
        text=True,
        check=False,
        cwd=PROJECT_ROOT,
    ).stdout.strip()
    processor = platform.processor() or platform.machine()
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        for line in cpuinfo.read_text(encoding="utf-8").splitlines():
            if line.startswith("model name"):
                processor = line.split(":", 1)[1].strip()
                break
    return f"revision {revision or 'unknown'}, Python {platform.python_version()}, {processor}"


def main(argv: Sequence[str] | None = None) -> int:
    """Print the three tables as Markdown and return the exit status."""
    parser = argparse.ArgumentParser(description="Measure the frame costs in the 3D Performance chapter.")
    parser.add_argument("--samples", type=int, default=5, help="runs per measurement; the median is reported")
    args = parser.parse_args(argv)
    print(f"Measured on {environment()}, median of {args.samples} runs.\n")
    print("| Example | Arguments | Frames | Time per frame |\n| --- | --- | --- | --- |")
    for directory, command, effect_args in EXAMPLE_ROWS:
        per_frame, frames = time_example(directory, command, effect_args, args.samples)
        print(f"| {command} | {' '.join(effect_args) or '-'} | {frames} | {per_frame:.1f} ms |")
    print("\n| Sphere, radius 20 | Time per step |\n| --- | --- |")
    for segments, rings, look in SPHERE_ROWS:
        made = look()
        name = type(made).__name__ + ('(back="dim")' if getattr(made, "back", "hide") == "dim" else "()")
        print(f"| {segments} by {rings}, `{name}` | {time_sphere(segments, rings, made, args.samples):.1f} ms |")
    print("\n| Mounted characters | Time per step |\n| --- | --- |")
    full_screen = "\n".join("x" * 200 for _ in range(50))
    for text, width, height in ((CONCEPT_INPUT, 80, 24), (full_screen, 200, 50)):
        per_step, count = time_mounts(text, width, height, args.samples)
        print(f"| {count} | {per_step:.1f} ms |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
