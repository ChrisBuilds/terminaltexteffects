"""Render effect demo animations without screen recording.

Each demo is rendered ahead of time with `tte --record`, so frame timing is exact and independent of machine
speed. The recording is converted to an asciicast holding only the effect canvas, which `agg` renders to a GIF
that needs no cropping or trimming. Output can be that GIF, a lossless animated WebP converted from it (the
default), or an MP4.

Requires `agg` on `PATH`, plus `gif2webp` for WebP output and `ffmpeg` for MP4 output. When `gifsicle` is
installed, `--gifsicle-lossy` applies lossy GIF compression.

Examples:
    ./.venv/bin/python tools/render_demos.py --list
    ./.venv/bin/python tools/render_demos.py beams matrix --formats gif,webp,mp4
    ./.venv/bin/python tools/render_demos.py --all --out docs/img/effects_demos
    ./.venv/bin/python tools/render_demos.py --guide --all --out docs/img/effectguide

"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from terminaltexteffects.engine._recording import RecordingReader

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "tests" / "testinput" / "demo.txt"
DEFAULT_OUT = PROJECT_ROOT / "build" / "demos"
GUIDE_EXAMPLES = PROJECT_ROOT / "docs" / "effectguide" / "examples"
TUTORIAL_INPUT = GUIDE_EXAMPLES / "tutorial_input.txt"
FORMATS = ("gif", "webp", "mp4")


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
    env = None
    if demo.effects_dir is not None:
        env = os.environ | {"TTE_DEV_EFFECTS_DIR": str(demo.effects_dir)}
    run(command, env)


def recording_to_cast(recording: Path, cast: Path, start_hold: float) -> bool:
    """Write the recording as an asciicast v2 file holding only the canvas.

    Every frame is drawn from the top-left corner with the cursor hidden, at the recording's frame period.
    The first frame is shown for an extra `start_hold` seconds.

    Returns:
        bool: Whether any frame contains non-ASCII text, which needs the `resvg` renderer in `agg`.

    """
    non_ascii = False
    with RecordingReader(recording) as reader, cast.open("w", encoding="utf-8") as out:
        header = reader.header
        period = 1 / header.frame_rate
        out.write(json.dumps({"version": 2, "width": header.width, "height": header.height}) + "\n")
        for index, frame in enumerate(reader.frames()):
            non_ascii = non_ascii or not frame.isascii()
            prefix = "\x1b[?25l\x1b[2J\x1b[H" if index == 0 else "\x1b[H"
            time = 0.0 if index == 0 else start_hold + index * period
            out.write(json.dumps([round(time, 6), "o", prefix + frame.replace("\n", "\r\n")]) + "\n")
    return non_ascii


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
        str(fps),
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


def render_webp(gif: Path, webp: Path) -> None:
    """Convert the GIF to a lossless animated WebP, which keeps every pixel and frame delay."""
    run(["gif2webp", "-quiet", "-min_size", str(gif), "-o", str(webp)])


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


def try_render(name: str, demo: Demo, out_dir: Path, args: argparse.Namespace) -> bool:
    """Render one demo, reporting a failure instead of raising.

    Returns:
        bool: Whether the demo rendered.

    """
    try:
        render(name, demo, out_dir, args.formats, fps=args.fps, gifsicle_lossy=args.gifsicle_lossy)
    except CommandError as error:
        print(f"{name}: {error}", file=sys.stderr)
        return False
    return True


def render(name: str, demo: Demo, out_dir: Path, formats: list[str], *, fps: int, gifsicle_lossy: int | None) -> None:
    """Render one demo to each requested format, named `<name>_demo.<format>`."""
    with tempfile.TemporaryDirectory(prefix="tte-demo-") as temp:
        work = Path(temp)
        record(demo, work / "demo.tterec")
        non_ascii = recording_to_cast(work / "demo.tterec", work / "demo.cast", demo.start_hold)
        gif = work / "demo.gif"
        render_gif(work / "demo.cast", gif, demo, fps=fps, non_ascii=non_ascii)
        # WebP and MP4 come from the uncompressed GIF so lossy GIF compression does not carry into them.
        if "webp" in formats:
            render_webp(gif, out_dir / f"{name}_demo.webp")
        if "mp4" in formats:
            render_mp4(gif, out_dir / f"{name}_demo.mp4")
        if "gif" in formats:
            if gifsicle_lossy is not None:
                compress_gif(gif, gifsicle_lossy)
            shutil.move(gif, out_dir / f"{name}_demo.gif")
    sizes = ", ".join(f"{fmt} {(out_dir / f'{name}_demo.{fmt}').stat().st_size // 1024} KB" for fmt in formats)
    print(f"{name}: {sizes}")


def required_tools(formats: list[str], *, gifsicle: bool) -> list[str]:
    """Return the external tools needed for the requested output."""
    tools = ["agg"]
    tools += ["gif2webp"] if "webp" in formats else []
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
    parser.add_argument("--fps", type=int, default=30, help="maximum output frame rate (default: 30)")
    parser.add_argument("--gifsicle-lossy", type=int, metavar="LEVEL", help="apply gifsicle lossy compression")
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
    if missing := [
        tool
        for tool in required_tools(args.formats, gifsicle=args.gifsicle_lossy is not None)
        if shutil.which(tool) is None
    ]:
        parser.error(f"missing required tools: {', '.join(missing)}")

    args.out.mkdir(parents=True, exist_ok=True)
    results = [try_render(name, available[name], args.out, args) for name in selected]
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
