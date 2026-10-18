"""Render effect demo animations without screen recording.

Each demo is recorded ahead of time with `tte --export`, so frame timing is exact and independent of machine
speed, then drawn as a lossless WebP or a GIF with the same Pillow renderer `tte --export` uses (see
`terminaltexteffects.utils.export`). Demos render in parallel, one per CPU core.

Requires Pillow, installed on Python 3.10 and later by `uv sync --group dev`.

Examples:
    ./.venv/bin/python tools/render_demos.py --list
    ./.venv/bin/python tools/render_demos.py beams matrix --formats gif,webp
    ./.venv/bin/python tools/render_demos.py --all --out docs/img/effects_demos
    ./.venv/bin/python tools/render_demos.py --guide --all --out docs/img/effectguide

"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from terminaltexteffects.engine._recording import RecordingReader, RecordingWriter
from terminaltexteffects.utils import export

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "tests" / "testinput" / "demo.txt"
DEFAULT_OUT = PROJECT_ROOT / "build" / "demos"
GUIDE_EXAMPLES = PROJECT_ROOT / "docs" / "effectguide" / "examples"
TUTORIAL_INPUT = GUIDE_EXAMPLES / "tutorial_input.txt"
CONCEPT_INPUT = GUIDE_EXAMPLES / "concept_input.txt"
COLOR_INPUT = GUIDE_EXAMPLES / "color_input.txt"
EXAMPLES_3D = GUIDE_EXAMPLES / "3d"
CANVAS_3D = ("--canvas-width", "80", "--canvas-height", "24", "--anchor-text", "c")
"""The 3D Effects chapters run every example on an 80 by 24 canvas, so shapes have room around the text."""
FORMATS = ("gif", "webp")
DEMO_SEED = 1
"""Every demo records with this seed, so the same code always records the same frames."""
MANIFEST = "demos.json"
"""Name of the file, beside the demos, that maps each demo to the fingerprint of what it was rendered from."""
RENDERER_SOURCES = tuple(
    PROJECT_ROOT / "terminaltexteffects" / "utils" / name for name in ("_animation.py", "export.py")
)
"""Code that turns a recording into a demo image, so a change to it marks every demo out of date."""
DEFAULT_FPS = 60
"""The highest output frame rate. Demos record at 60 fps, so WebP output keeps every frame."""


@dataclass(frozen=True)
class Demo:
    """One demo animation: the effect to run and how to render it."""

    effect: str
    effect_args: tuple[str, ...] = ()
    tte_args: tuple[str, ...] = ()
    input_file: Path = DEFAULT_INPUT
    frame_rate: int = 60
    start_hold: float = 0.0
    end_hold: float = 2.0
    effects_dir: Path | None = None
    end_on_text: bool = True
    """Keep the closing frames that show only the finished text. The 3D examples swap their shapes for the text when
    they finish, and that text would open each loop of the animation, so their demos end on the last shape frame."""


# Built-in effects render from `demo.txt` with default options. Add an entry here to change the options for a
# demo, or to add a demo that is not named after its effect.
DEMO_OVERRIDES: dict[str, Demo] = {}

# Effect Guide visuals. Each one shows exactly what the reader sees when running the command next to it, so it uses
# the same input file. Each example effect lives in its own directory under `docs/effectguide/examples/`, which is
# loaded through `TTE_DEV_EFFECTS_DIR` so every tutorial step can keep the same command name.
GUIDE_DEMOS: dict[str, Demo] = {
    "spray_goal": Demo(effect="spray", input_file=TUTORIAL_INPUT),
    "myspray_step1": Demo(effect="myspray", input_file=TUTORIAL_INPUT, effects_dir=GUIDE_EXAMPLES / "myspray_step1"),
    "myspray_step2": Demo(effect="myspray", input_file=TUTORIAL_INPUT, effects_dir=GUIDE_EXAMPLES / "myspray_step2"),
    "myspray_step3": Demo(effect="myspray", input_file=TUTORIAL_INPUT, effects_dir=GUIDE_EXAMPLES / "myspray_step3"),
    "myspray_step4": Demo(effect="myspray", input_file=TUTORIAL_INPUT, effects_dir=GUIDE_EXAMPLES / "myspray_step4"),
    "myspray_step5": Demo(effect="myspray", input_file=TUTORIAL_INPUT, effects_dir=GUIDE_EXAMPLES / "myspray_step5"),
    "myspray_step7": Demo(
        effect="myspray",
        tte_args=("--existing-color-handling", "dynamic"),
        input_file=COLOR_INPUT,
        effects_dir=GUIDE_EXAMPLES / "myspray_step7",
    ),
    "spray_colors": Demo(effect="spray", tte_args=("--existing-color-handling", "dynamic"), input_file=COLOR_INPUT),
    "myspray_step6": Demo(effect="myspray", input_file=TUTORIAL_INPUT, effects_dir=GUIDE_EXAMPLES / "myspray_step6"),
    "myspray_step6_options": Demo(
        effect="myspray",
        effect_args=("--spray-position", "center", "--final-gradient-direction", "radial"),
        input_file=TUTORIAL_INPUT,
        effects_dir=GUIDE_EXAMPLES / "myspray_step6",
    ),
    **{
        f"reveal_{order}": Demo(
            effect="reveal",
            effect_args=("--order", order),
            input_file=CONCEPT_INPUT,
            frame_rate=frame_rate,
            effects_dir=GUIDE_EXAMPLES / "reveal",
        )
        # The Characters chapter shows each command with this frame rate, so the demo plays at the reader's speed.
        for order, frame_rate in (
            ("row_top_to_bottom", 8),
            ("diagonal_top_left_to_bottom_right", 30),
            ("circle_center_to_outside", 15),
            ("spiral_clockwise", 60),
        )
    },
    "travel_linear": Demo(effect="travel", input_file=CONCEPT_INPUT, effects_dir=GUIDE_EXAMPLES / "travel"),
    **{
        f"travel_{ease}": Demo(
            effect="travel",
            effect_args=("--ease", ease),
            input_file=CONCEPT_INPUT,
            effects_dir=GUIDE_EXAMPLES / "travel",
        )
        for ease in ("out_expo", "in_out_quart", "out_bounce")
    },
    "travel_curve": Demo(
        effect="travel",
        effect_args=("--curve",),
        input_file=CONCEPT_INPUT,
        effects_dir=GUIDE_EXAMPLES / "travel",
    ),
    "hop": Demo(effect="hop", input_file=CONCEPT_INPUT, effects_dir=GUIDE_EXAMPLES / "hop"),
    "glow": Demo(effect="glow", input_file=CONCEPT_INPUT, effects_dir=GUIDE_EXAMPLES / "glow"),
    "glow_slow": Demo(
        effect="glow",
        effect_args=("--frame-duration", "10"),
        input_file=CONCEPT_INPUT,
        effects_dir=GUIDE_EXAMPLES / "glow",
    ),
    **{
        f"glow_sync_{sync}": Demo(
            effect="glow",
            effect_args=("--sync", sync),
            input_file=CONCEPT_INPUT,
            effects_dir=GUIDE_EXAMPLES / "glow",
        )
        for sync in ("distance", "step")
    },
    **{
        f"paint_{direction}": Demo(
            effect="paint",
            effect_args=("--direction", direction),
            input_file=CONCEPT_INPUT,
            effects_dir=GUIDE_EXAMPLES / "paint",
        )
        for direction in ("vertical", "horizontal", "radial", "diagonal")
    },
    **{
        f"paint_colors_{handling}": Demo(
            effect="paint",
            tte_args=("--existing-color-handling", handling),
            input_file=COLOR_INPUT,
            effects_dir=GUIDE_EXAMPLES / "paint",
        )
        for handling in ("ignore", "always", "dynamic")
    },
    "gather": Demo(effect="gather", input_file=CONCEPT_INPUT, effects_dir=GUIDE_EXAMPLES / "gather"),
    "gather_columns": Demo(
        effect="gather",
        effect_args=("--gather-order", "column_left_to_right"),
        input_file=CONCEPT_INPUT,
        effects_dir=GUIDE_EXAMPLES / "gather",
    ),
    "sparks": Demo(effect="sparks", input_file=CONCEPT_INPUT, effects_dir=GUIDE_EXAMPLES / "sparks"),
    "sparks_few": Demo(
        effect="sparks",
        effect_args=("--max-sparks", "8"),
        input_file=CONCEPT_INPUT,
        effects_dir=GUIDE_EXAMPLES / "sparks",
    ),
    **{
        f"grow_{algorithm}": Demo(
            effect="grow",
            effect_args=("--algorithm", algorithm),
            input_file=CONCEPT_INPUT,
            effects_dir=GUIDE_EXAMPLES / "grow",
        )
        for algorithm in ("prims_simple", "recursive_backtracker", "aldous_broder")
    },
    "wave": Demo(effect="wave", input_file=CONCEPT_INPUT, effects_dir=GUIDE_EXAMPLES / "wave"),
    **{
        name: Demo(
            effect=effect,
            effect_args=effect_args,
            tte_args=CANVAS_3D,
            input_file=CONCEPT_INPUT,
            effects_dir=EXAMPLES_3D / effect,
            end_on_text=False,
        )
        for name, effect, effect_args in (
            ("cubes", "cubes", ()),
            ("cubes_wireframe", "cubes", ("--wireframe",)),
            ("axes", "axes", ()),
            ("cells", "cells", ()),
            ("orbit", "orbit", ()),
            ("turns_axes", "turns", ()),
            ("turns_tumble", "turns", ("--mode", "tumble")),
            ("turns_rest", "turns", ("--mode", "rest")),
            ("lens_0", "lens", ("--perspective", "0")),
            ("lens_1", "lens", ()),
            ("lens_2", "lens", ("--perspective", "2")),
            ("depth", "depth", ()),
            ("depth_see_through", "depth", ("--see-through",)),
            ("card", "card", ()),
            ("card_hide_back", "card", ("--hide-back",)),
            ("gallery", "gallery", ()),
            ("star", "star", ()),
            ("star_wireframe", "star", ("--wireframe",)),
            ("light", "light", ()),
            ("light_torus", "light", ("--shape", "torus", "--symbols", "░▒▓█")),
            ("texture_grid", "texture", ()),
            ("texture_text", "texture", ("--text",)),
            ("handoff", "handoff", ()),
            ("logo", "logo", ()),
            ("die", "die", ()),
            ("globe", "globe", ()),
            ("ticker", "ticker", ("--message", " HELLO ·")),
            ("wireframes", "wireframes", ()),
            ("surfaces", "surfaces", ()),
            ("eases", "eases", ()),
            ("detail", "detail", ()),
            ("detail_wireframe", "detail", ("--wireframe",)),
        )
    },
    "cameraorbit": Demo(
        effect="cameraorbit",
        tte_args=("--canvas-width", "80", "--canvas-height", "32", "--anchor-text", "c"),
        input_file=CONCEPT_INPUT,
        effects_dir=EXAMPLES_3D / "cameraorbit",
        end_on_text=False,
    ),
    # The Spin tutorial: each step under one command name. Step 6 is the finished effect.
    **{
        f"myspin_step{step}": Demo(
            effect="myspin",
            tte_args=CANVAS_3D,
            input_file=CONCEPT_INPUT,
            effects_dir=EXAMPLES_3D / f"myspin_step{step}",
            end_on_text=False,
        )
        for step in range(1, 7)
    },
    "myspin_step6_options": Demo(
        effect="myspin",
        effect_args=(
            "--spin-turns",
            "1",
            "--start-distance",
            "60",
            "--hide-back",
            "--final-gradient-stops",
            "ffb000",
            "ff5fd7",
        ),
        tte_args=CANVAS_3D,
        input_file=CONCEPT_INPUT,
        effects_dir=EXAMPLES_3D / "myspin_step6",
        end_on_text=False,
    ),
    "travel_canvas": Demo(
        effect="travel",
        tte_args=("--canvas-width", "60", "--canvas-height", "14", "--anchor-text", "c"),
        input_file=CONCEPT_INPUT,
        effects_dir=GUIDE_EXAMPLES / "travel",
    ),
}


class CommandError(Exception):
    """Raised when an external command fails."""


def run(command: list[str], env: dict[str, str] | None = None) -> None:
    """Run a command, raising `CommandError` with its output when it fails."""
    result = subprocess.run(  # noqa: S603 - Separated arguments; no shell.
        command,
        check=False,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        message = f"{Path(command[0]).name} exited with {result.returncode}: {(result.stderr or result.stdout).strip()}"
        raise CommandError(message)


def builtin_effects() -> list[str]:
    """Return the built-in effect command names."""
    from terminaltexteffects.__main__ import build_parser  # noqa: PLC0415

    parser, _ = build_parser(include_user_effects=False)
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return sorted(action.choices)
    message = "The CLI parser has no effect subcommands"
    raise RuntimeError(message)


def demos() -> dict[str, Demo]:
    """Return every demo by name, with overrides applied."""
    return {name: Demo(effect=name) for name in builtin_effects()} | DEMO_OVERRIDES


def record(demo: Demo, path: Path) -> None:
    """Render the demo effect to a recording with `tte --export`."""
    command = [
        sys.executable,
        "-m",
        "terminaltexteffects",
        "--input-file",
        str(demo.input_file),
        "--frame-rate",
        str(demo.frame_rate),
        "--seed",
        str(DEMO_SEED),
        "--export",
        str(path),
        *demo.tte_args,
        demo.effect,
        *demo.effect_args,
    ]
    if demo.effects_dir is None:
        run(command)
        return
    # An empty config dir keeps an installed copy of a guide effect from clashing with the development copy.
    with tempfile.TemporaryDirectory() as config_home:
        run(command, os.environ | {"TTE_DEV_EFFECTS_DIR": str(demo.effects_dir), "XDG_CONFIG_HOME": config_home})


def drop_final_text(recording: Path) -> None:
    """Remove the frames at the end of `recording` that repeat its last frame, the finished text."""
    with RecordingReader(recording) as reader:
        header = reader.header
        frames = list(reader.frames())
    while len(frames) > 1 and frames[-2] == frames[-1]:
        frames.pop()
    with RecordingWriter(recording, header) as writer:
        writer.begin_segment("demo")
        for frame in frames[:-1] or frames:
            writer.write_frame(frame)


def fingerprint(recording: Path, demo: Demo, fps: int) -> str:
    """Return a digest of the frames in `recording` and everything else that decides how the demo is drawn.

    Two renders with the same fingerprint draw the same animation, so a demo whose fingerprint no longer matches the
    one in its `MANIFEST` is out of date with the code it shows.
    """
    digest = hashlib.sha256()
    with RecordingReader(recording) as reader:
        settings = {
            "width": reader.header.width,
            "height": reader.header.height,
            "frame_rate": reader.header.frame_rate,
            "fps": min(fps, demo.frame_rate),
            "start_hold": demo.start_hold,
            "end_hold": demo.end_hold,
            "renderer": [
                hashlib.sha256(source.read_bytes().replace(b"\r\n", b"\n")).hexdigest() for source in RENDERER_SOURCES
            ],
        }
        digest.update(json.dumps(settings, sort_keys=True).encode())
        for frame in reader.frames():
            digest.update(b"\0" + frame.encode())
    return digest.hexdigest()


def read_manifest(out_dir: Path) -> dict[str, str]:
    """Return the demo fingerprints recorded in `out_dir`, or none if it has no manifest."""
    path = out_dir / MANIFEST
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def write_manifest(out_dir: Path, fingerprints: dict[str, str]) -> None:
    """Add or replace the fingerprints of the demos just rendered in `out_dir`'s manifest."""
    manifest = read_manifest(out_dir) | fingerprints
    (out_dir / MANIFEST).write_text(json.dumps(dict(sorted(manifest.items())), indent=2) + "\n", encoding="utf-8")


def record_for_render(demo: Demo, path: Path) -> None:
    """Record the demo as it is drawn: with the closing text dropped when the demo doesn't end on it."""
    record(demo, path)
    if not demo.end_on_text:
        drop_final_text(path)


@dataclass(frozen=True)
class RenderOptions:
    """Command-line choices that apply to every demo."""

    formats: tuple[str, ...]
    font: str | None = None
    fps: int = DEFAULT_FPS
    fallback_fonts: tuple[str, ...] = ()


def try_render(name: str, demo: Demo, out_dir: Path, options: RenderOptions) -> tuple[str, str | None]:
    """Render one demo, reporting a failure instead of raising.

    Returns:
        tuple[str, str | None]: The demo's file sizes or the error, and its fingerprint if it rendered.

    """
    try:
        return render(name, demo, out_dir, options)
    except (CommandError, export.ExportError) as error:
        return f"{name}: {error}", None


def render(name: str, demo: Demo, out_dir: Path, options: RenderOptions) -> tuple[str, str]:
    """Render one demo to each requested format, named `<name>_demo.<format>`.

    Returns:
        tuple[str, str]: The rendered files' sizes, and the demo's fingerprint.

    """
    missing: set[str] = set()
    with tempfile.TemporaryDirectory(prefix="tte-demo-") as temp:
        recording = Path(temp) / "demo.tterec"
        record_for_render(demo, recording)
        demo_fingerprint = fingerprint(recording, demo, options.fps)
        for fmt in options.formats:
            missing |= export.export_recording(
                recording,
                out_dir / f"{name}_demo.{fmt}",
                export.format_for(Path(f"demo.{fmt}")),
                fps=min(options.fps, demo.frame_rate),
                font=options.font,
                fallback_fonts=options.fallback_fonts,
                start_hold=demo.start_hold,
                end_hold=demo.end_hold,
            )
    sizes = ", ".join(f"{fmt} {(out_dir / f'{name}_demo.{fmt}').stat().st_size // 1024} KB" for fmt in options.formats)
    note = f" (no font has {' '.join(sorted(missing))}; pass --fallback-font FONT)" if missing else ""
    return f"{name}: {sizes}{note}", demo_fingerprint


def parse_formats(value: str) -> list[str]:
    """Parse a comma-separated list of output formats."""
    formats = [fmt.strip() for fmt in value.split(",") if fmt.strip()]
    unknown = sorted(set(formats) - set(FORMATS))
    if unknown or not formats:
        message = f"formats must be a comma-separated subset of {', '.join(FORMATS)}"
        raise argparse.ArgumentTypeError(message)
    return formats


def main() -> int:
    """Render the selected demos."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("demos", nargs="*", help="demo names to render (see --list)")
    parser.add_argument("--all", action="store_true", help="render every demo")
    parser.add_argument("--guide", action="store_true", help="select Effect Guide demos instead of effect demos")
    parser.add_argument("--list", action="store_true", help="list demo names and exit")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output directory (default: build/demos)")
    parser.add_argument(
        "--formats",
        type=parse_formats,
        default=["webp"],
        help="comma-separated output formats: gif, webp (default: webp)",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=DEFAULT_FPS,
        help=f"maximum output frame rate (default: {DEFAULT_FPS})",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=os.cpu_count() or 1,
        help="demos to render at once (default: one per CPU core)",
    )
    parser.add_argument("--font", help="font path or file name (default: the first installed monospace font)")
    parser.add_argument(
        "--fallback-font",
        action="append",
        default=[],
        metavar="FONT",
        help="font for symbols the main font lacks, tried before the built-in list (repeatable)",
    )
    args = parser.parse_args()

    available = GUIDE_DEMOS if args.guide else demos()
    if args.list:
        print("\n".join(available))
        return 0
    selected = list(available) if args.all else list(dict.fromkeys(args.demos))
    if not selected:
        parser.error("name at least one demo, or pass --all")
    if unknown := [name for name in selected if name not in available]:
        parser.error(f"unknown demo: {', '.join(unknown)}")
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")
    if problem := export.format_problem(export.FORMATS[1]):
        parser.error(problem)
    from terminaltexteffects.utils._animation import Fonts, RenderError  # noqa: PLC0415 (needs Pillow)

    try:
        Fonts(args.font, args.fallback_font)
    except RenderError as error:
        parser.error(str(error))
    options = RenderOptions(
        formats=tuple(args.formats),
        font=args.font,
        fps=args.fps,
        fallback_fonts=tuple(args.fallback_font),
    )

    args.out.mkdir(parents=True, exist_ok=True)
    # Each demo records and encodes on one core, so demos render in parallel.
    with ProcessPoolExecutor(max_workers=args.jobs) as executor:
        futures = {executor.submit(try_render, name, available[name], args.out, options): name for name in selected}
        fingerprints: dict[str, str] = {}
        for future in as_completed(futures):
            message, demo_fingerprint = future.result()
            print(message, file=sys.stderr if demo_fingerprint is None else sys.stdout, flush=True)
            if demo_fingerprint is not None:
                fingerprints[futures[future]] = demo_fingerprint
    # The manifest describes the committed WebP demos, so a GIF-only render leaves it alone.
    if "webp" in options.formats:
        write_manifest(args.out, fingerprints)
    return 0 if len(fingerprints) == len(selected) else 1


if __name__ == "__main__":
    raise SystemExit(main())
