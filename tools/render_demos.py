"""Render effect demo animations without screen recording.

Each demo is rendered ahead of time with `tte --record`, so frame timing is exact and independent of machine
speed. WebP output, the default, is drawn straight from the recording with Pillow and encoded by `img2webp` with
near-lossless preprocessing, keeping every color with no visible change (see `render_webp`). GIF and MP4 output
convert the recording to an asciicast holding only the effect canvas, which `agg` renders to a GIF that needs no
cropping or trimming. Demos render in parallel, one per CPU core.

Requires `img2webp` from libwebp for WebP output, and `agg` 1.7 or later for GIF and MP4 output, plus `ffmpeg` for
MP4. When `gifsicle` is installed, `--gifsicle-lossy` applies lossy GIF compression.

Examples:
    ./.venv/bin/python tools/render_demos.py --list
    ./.venv/bin/python tools/render_demos.py beams matrix --formats gif,webp,mp4
    ./.venv/bin/python tools/render_demos.py --all --out docs/img/effects_demos
    ./.venv/bin/python tools/render_demos.py --guide --all --out docs/img/effectguide

"""

from __future__ import annotations

import argparse
import functools
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from terminaltexteffects.utils.export import agg_fps_cap, recording_to_cast

# The WebP renderer needs Pillow, which is only installed on Python 3.10 and later, so it is imported when used.
if TYPE_CHECKING:
    from tools.render_webp import Fonts

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "tests" / "testinput" / "demo.txt"
DEFAULT_OUT = PROJECT_ROOT / "build" / "demos"
GUIDE_EXAMPLES = PROJECT_ROOT / "docs" / "effectguide" / "examples"
TUTORIAL_INPUT = GUIDE_EXAMPLES / "tutorial_input.txt"
CONCEPT_INPUT = GUIDE_EXAMPLES / "concept_input.txt"
COLOR_INPUT = GUIDE_EXAMPLES / "color_input.txt"
FORMATS = ("gif", "webp", "mp4")
NEAR_LOSSLESS = 60
"""The WebP near-lossless level, which changes pixel values by a few steps at most and shrinks most demos."""
NEAR_LOSSLESS_OFF = 100
"""The near-lossless level that leaves WebP output lossless."""
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
    agg_args: tuple[str, ...] = field(default=())
    effects_dir: Path | None = None


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
    """Render the demo effect to a recording with `tte --record`."""
    command = [
        sys.executable,
        "-m",
        "terminaltexteffects",
        "--input-file",
        str(demo.input_file),
        "--frame-rate",
        str(demo.frame_rate),
        "--record",
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


def render_gif(cast: Path, gif: Path, demo: Demo, *, fps: int, non_ascii: bool) -> None:
    """Render the asciicast to a GIF with `agg`."""
    command = [
        "agg",
        "--quiet",
        "--theme",
        "asciinema",
        "--font-size",
        "14",
        "--fps-cap",
        str(agg_fps_cap(min(fps, demo.frame_rate))),
        "--last-frame-duration",
        str(demo.end_hold),
        *(["--renderer", "resvg"] if non_ascii else []),
        *demo.agg_args,
        str(cast),
        str(gif),
    ]
    run(command)


def compress_gif(gif: Path, lossy: int) -> None:
    """Apply `gifsicle` optimization and lossy compression to the GIF in place."""
    run(["gifsicle", "--batch", "-O3", f"--lossy={lossy}", str(gif)])


def render_mp4(gif: Path, mp4: Path) -> None:
    """Convert the GIF to an H.264 MP4 that browsers can autoplay inline."""
    command = [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-i",
        str(gif),
        "-vf",
        "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        "-c:v",
        "libx264",
        "-preset",
        "veryslow",
        "-tune",
        "animation",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-an",
        str(mp4),
    ]
    run(command)


@dataclass(frozen=True)
class RenderOptions:
    """Command-line choices that apply to every demo.

    `near_lossless` applies to WebP output.
    """

    formats: tuple[str, ...]
    font: str
    fps: int = DEFAULT_FPS
    gifsicle_lossy: int | None = None
    near_lossless: int = NEAR_LOSSLESS
    fallback_fonts: tuple[str, ...] = ()


@functools.cache
def load_fonts(font: str, fallback_fonts: tuple[str, ...]) -> Fonts:
    """Load the WebP fonts once in each worker process."""
    from tools.render_webp import Fonts  # noqa: PLC0415

    return Fonts(font, fallback_fonts)


def try_render(name: str, demo: Demo, out_dir: Path, options: RenderOptions) -> tuple[bool, str]:
    """Render one demo, reporting a failure instead of raising.

    Returns:
        tuple[bool, str]: Whether the demo rendered, and its file sizes or the error.

    """
    try:
        return True, render(name, demo, out_dir, options)
    except CommandError as error:
        return False, f"{name}: {error}"


def render(name: str, demo: Demo, out_dir: Path, options: RenderOptions) -> str:
    """Render one demo to each requested format, named `<name>_demo.<format>`, and return their sizes."""
    formats = options.formats
    fps = min(options.fps, demo.frame_rate)
    near_lossless = options.near_lossless
    with tempfile.TemporaryDirectory(prefix="tte-demo-") as temp:
        work = Path(temp)
        record(demo, work / "demo.tterec")
        if "webp" in formats:
            from tools.render_webp import Encoding, RenderError, render_webp  # noqa: PLC0415

            try:
                render_webp(
                    work / "demo.tterec",
                    out_dir / f"{name}_demo.webp",
                    fps=fps,
                    encoding=Encoding(None if near_lossless == NEAR_LOSSLESS_OFF else near_lossless),
                    fonts=load_fonts(options.font, options.fallback_fonts),
                    start_hold=demo.start_hold,
                    end_hold=demo.end_hold,
                )
            except RenderError as error:
                raise CommandError(str(error)) from error
        if "gif" in formats or "mp4" in formats:
            non_ascii = recording_to_cast(work / "demo.tterec", work / "demo.cast", demo.start_hold)
            gif = work / "demo.gif"
            render_gif(work / "demo.cast", gif, demo, fps=fps, non_ascii=non_ascii)
            # MP4 comes from the uncompressed GIF so lossy GIF compression does not carry into it.
            if "mp4" in formats:
                render_mp4(gif, out_dir / f"{name}_demo.mp4")
            if "gif" in formats:
                if options.gifsicle_lossy is not None:
                    compress_gif(gif, options.gifsicle_lossy)
                shutil.move(gif, out_dir / f"{name}_demo.gif")
    sizes = ", ".join(f"{fmt} {(out_dir / f'{name}_demo.{fmt}').stat().st_size // 1024} KB" for fmt in formats)
    return f"{name}: {sizes}"


def required_tools(formats: list[str], *, gifsicle: bool) -> list[str]:
    """Return the external tools needed for the requested output."""
    tools = ["agg"] if "gif" in formats or "mp4" in formats else []
    tools += ["img2webp"] if "webp" in formats else []
    tools += ["ffmpeg"] if "mp4" in formats else []
    tools += ["gifsicle"] if gifsicle else []
    return tools


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
        help="comma-separated output formats: gif, webp, mp4 (default: webp)",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=DEFAULT_FPS,
        help=f"maximum output frame rate (default: {DEFAULT_FPS})",
    )
    parser.add_argument("--gifsicle-lossy", type=int, metavar="LEVEL", help="apply gifsicle lossy compression")
    parser.add_argument(
        "--near-lossless",
        type=int,
        default=NEAR_LOSSLESS,
        choices=range(101),
        metavar="LEVEL",
        help=f"WebP near-lossless level for every demo, from 0 (strongest) to {NEAR_LOSSLESS_OFF} (lossless) "
        f"(default: {NEAR_LOSSLESS})",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=os.cpu_count() or 1,
        help="demos to render at once (default: one per CPU core)",
    )
    parser.add_argument("--font", help="font path or file name for WebP output (default: DejaVu Sans Mono)")
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
    selected = list(available) if args.all else args.demos
    if not selected:
        parser.error("name at least one demo, or pass --all")
    if unknown := [name for name in selected if name not in available]:
        parser.error(f"unknown demo: {', '.join(unknown)}")
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")
    if missing := [
        tool
        for tool in required_tools(args.formats, gifsicle=args.gifsicle_lossy is not None)
        if shutil.which(tool) is None
    ]:
        parser.error(f"missing required tools: {', '.join(missing)}")

    font = args.font or ""
    if "webp" in args.formats:
        try:
            from tools.render_webp import FONT, RenderError  # noqa: PLC0415
        except ImportError as error:
            parser.error(f"WebP output needs Pillow, installed on Python 3.10 or later ({error})")
        font = font or FONT
        try:
            load_fonts(font, tuple(args.fallback_font))
        except RenderError as error:
            parser.error(str(error))
    options = RenderOptions(
        formats=tuple(args.formats),
        font=font,
        fps=args.fps,
        gifsicle_lossy=args.gifsicle_lossy,
        near_lossless=args.near_lossless,
        fallback_fonts=tuple(args.fallback_font),
    )

    args.out.mkdir(parents=True, exist_ok=True)
    # Each demo records and encodes on one core, so demos render in parallel.
    with ProcessPoolExecutor(max_workers=args.jobs) as executor:
        futures = [executor.submit(try_render, name, available[name], args.out, options) for name in selected]
        results = []
        for future in as_completed(futures):
            rendered, message = future.result()
            print(message, file=sys.stdout if rendered else sys.stderr, flush=True)
            results.append(rendered)
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
