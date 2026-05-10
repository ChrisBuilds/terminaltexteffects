"""Benchmark TerminalTextEffects effect rendering without terminal I/O.

This script intentionally uses only the Python standard library so it can run in
any development checkout that can import terminaltexteffects.
"""

from __future__ import annotations

import argparse
import cProfile
import io
import json
import pstats
import random
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from terminaltexteffects import __main__ as tte_main
from terminaltexteffects.effects import effect_colorshift, effect_matrix, effect_thunderstorm
from terminaltexteffects.engine.terminal import TerminalConfig

if TYPE_CHECKING:
    from collections.abc import Sequence

    from terminaltexteffects.engine.base_effect import BaseEffect

DEFAULT_SAMPLES = 7
DEFAULT_WARMUPS = 2
DEFAULT_SEED = 1337

INPUT_PRESETS = {
    "small": "TerminalTextEffects",
    "medium": (
        "0123456789abcdefg\n"
        "123456789abcdefgh\n"
        "23456789abcdefghi\n"
        "3456789abcdefghij\n"
        "456789abcdefghijk"
    ),
    "large": (
        "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ\n"
        "123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0\n"
        "23456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01\n"
        "3456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ012\n"
        "456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123\n"
        "56789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01234\n"
        "6789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ012345\n"
        "789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456\n"
        "89abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01234567\n"
        "9abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ012345678"
    ),
    "wide": "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ" * 2,
    "tall": "\n".join(f"{index:02d} TerminalTextEffects" for index in range(30)),
    "color": (
        "\x1b[38;5;231m....\x1b[39m....| "
        "\x1b[38;5;95m\x1b[48;5;128mggggggg\x1b[0m "
        "\x1b[38;5;180mggggggg \x1b[38;5;146m:gggggg; "
        "\x1b[38;5;64mggggggg \x1b[38;5;182mggggggg"
    ),
}


@dataclass(frozen=True)
class IterationResult:
    """Timing and output details for one benchmark iteration."""

    build_seconds: float
    render_seconds: float
    total_seconds: float
    frames: int
    output_characters: int


def _effect_classes() -> dict[str, type[BaseEffect[Any]]]:
    """Return discovered built-in and plugin effect classes keyed by CLI command."""
    _, effect_resource_map = tte_main.build_parser()
    return {effect_name: effect_class for effect_name, (effect_class, _) in effect_resource_map.items()}


def _make_input_data(input_preset: str) -> str:
    """Return benchmark input for a named preset."""
    if input_preset == "generated":
        return "\n".join(
            "".join(chr(65 + ((row + column) % 26)) for column in range(80)) for row in range(24)
        )
    try:
        return INPUT_PRESETS[input_preset]
    except KeyError as exc:
        msg = f"Unknown input preset: {input_preset}"
        raise ValueError(msg) from exc


def _make_terminal_config() -> TerminalConfig:
    """Create a terminal config suitable for performance measurement."""
    terminal_config = TerminalConfig._build_config()
    terminal_config.frame_rate = 0
    terminal_config.canvas_width = -1
    terminal_config.canvas_height = -1
    return terminal_config


def _shorten_long_running_effect(effect_instance: BaseEffect[Any]) -> None:
    """Keep benchmark scenarios focused on renderer speed instead of long hold phases."""
    if isinstance(effect_instance, effect_matrix.Matrix):
        effect_instance.effect_config.rain_time = 1
    elif isinstance(effect_instance, effect_thunderstorm.Thunderstorm):
        effect_instance.effect_config.storm_time = 1
    elif isinstance(effect_instance, effect_colorshift.ColorShift):
        effect_instance.effect_config.cycles = 2


def run_iteration(effect_class: type[BaseEffect[Any]], input_data: str, seed: int) -> IterationResult:
    """Run one effect iteration and return timing details."""
    random.seed(seed)
    effect_instance = effect_class(input_data)
    effect_instance.terminal_config = _make_terminal_config()
    _shorten_long_running_effect(effect_instance)

    build_start = time.perf_counter()
    effect_iterator = iter(effect_instance)
    build_seconds = time.perf_counter() - build_start

    frames = 0
    output_characters = 0
    render_start = time.perf_counter()
    for frame in effect_iterator:
        frames += 1
        output_characters += len(frame)
    render_seconds = time.perf_counter() - render_start

    return IterationResult(
        build_seconds=build_seconds,
        render_seconds=render_seconds,
        total_seconds=build_seconds + render_seconds,
        frames=frames,
        output_characters=output_characters,
    )


def _stats(values: Sequence[float]) -> dict[str, float]:
    """Return summary statistics for a numeric sequence."""
    if not values:
        msg = "Cannot summarize an empty sequence"
        raise ValueError(msg)
    return {
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


def summarize_iterations(results: Sequence[IterationResult]) -> dict[str, Any]:
    """Return stable benchmark summary data for completed sample iterations."""
    if not results:
        msg = "Cannot summarize zero benchmark iterations"
        raise ValueError(msg)
    first_result = results[0]
    return {
        "build_seconds": _stats([result.build_seconds for result in results]),
        "render_seconds": _stats([result.render_seconds for result in results]),
        "total_seconds": _stats([result.total_seconds for result in results]),
        "frames": first_result.frames,
        "output_characters": first_result.output_characters,
        "frame_counts": [result.frames for result in results],
        "output_character_counts": [result.output_characters for result in results],
    }


def run_benchmark(
    *,
    effect_name: str,
    effect_class: type[BaseEffect[Any]],
    input_preset: str,
    samples: int,
    warmups: int,
    seed: int,
) -> dict[str, Any]:
    """Run warmups and timed samples for one effect scenario."""
    input_data = _make_input_data(input_preset)
    for warmup_index in range(warmups):
        run_iteration(effect_class, input_data, seed + warmup_index)
    sample_results = [
        run_iteration(effect_class, input_data, seed + warmups + sample_index) for sample_index in range(samples)
    ]
    return {
        "effect": effect_name,
        "input_preset": input_preset,
        "samples": samples,
        "warmups": warmups,
        "seed": seed,
        "summary": summarize_iterations(sample_results),
    }


def run_profile(effect_class: type[BaseEffect[Any]], input_preset: str, seed: int) -> str:
    """Profile one benchmark iteration and return a compact pstats report."""
    input_data = _make_input_data(input_preset)
    profiler = cProfile.Profile()
    profiler.enable()
    run_iteration(effect_class, input_data, seed)
    profiler.disable()
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream).strip_dirs().sort_stats("cumtime")
    stats.print_stats(40)
    return stream.getvalue()


def build_report(results: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Wrap scenario results with report metadata."""
    return {
        "tool": "tools/perf/benchmark_effects.py",
        "schema_version": 1,
        "python": sys.version.split()[0],
        "results": list(results),
    }


def _load_report(path: Path) -> dict[str, Any]:
    """Load a benchmark report JSON file."""
    with path.open(encoding="utf-8") as report_file:
        loaded_report = json.load(report_file)
    if not isinstance(loaded_report, dict) or "results" not in loaded_report:
        msg = f"Invalid benchmark report: {path}"
        raise ValueError(msg)
    return loaded_report


def _percent_delta(baseline: float, candidate: float) -> float | None:
    """Return percentage change from baseline to candidate."""
    if baseline == 0:
        return None
    return ((candidate - baseline) / baseline) * 100


def compare_reports(baseline_report: dict[str, Any], candidate_report: dict[str, Any]) -> str:
    """Return a human-readable comparison between two benchmark reports."""
    candidate_by_key = {
        (result["effect"], result["input_preset"]): result for result in candidate_report.get("results", [])
    }
    lines = ["effect,input,metric,baseline,candidate,delta_percent"]
    for baseline_result in baseline_report.get("results", []):
        key = (baseline_result["effect"], baseline_result["input_preset"])
        candidate_result = candidate_by_key.get(key)
        if candidate_result is None:
            lines.append(f"{key[0]},{key[1]},missing_candidate,,,,")
            continue
        for metric in ("build_seconds", "render_seconds", "total_seconds"):
            baseline_mean = float(baseline_result["summary"][metric]["mean"])
            candidate_mean = float(candidate_result["summary"][metric]["mean"])
            delta = _percent_delta(baseline_mean, candidate_mean)
            delta_text = "n/a" if delta is None else f"{delta:+.2f}"
            lines.append(
                f"{key[0]},{key[1]},{metric},{baseline_mean:.9f},{candidate_mean:.9f},{delta_text}",
            )
        baseline_frames = baseline_result["summary"]["frames"]
        candidate_frames = candidate_result["summary"]["frames"]
        frame_delta = candidate_frames - baseline_frames
        lines.append(f"{key[0]},{key[1]},frames,{baseline_frames},{candidate_frames},{frame_delta}")
        baseline_chars = baseline_result["summary"]["output_characters"]
        candidate_chars = candidate_result["summary"]["output_characters"]
        output_character_delta = candidate_chars - baseline_chars
        lines.append(f"{key[0]},{key[1]},output_characters,{baseline_chars},{candidate_chars},{output_character_delta}")
    return "\n".join(lines)


def _positive_int(value: str) -> int:
    """Parse a positive integer argument."""
    parsed_value = int(value)
    if parsed_value < 1:
        msg = "value must be >= 1"
        raise argparse.ArgumentTypeError(msg)
    return parsed_value


def _non_negative_int(value: str) -> int:
    """Parse a non-negative integer argument."""
    parsed_value = int(value)
    if parsed_value < 0:
        msg = "value must be >= 0"
        raise argparse.ArgumentTypeError(msg)
    return parsed_value


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the benchmark CLI parser."""
    parser = argparse.ArgumentParser(description="Benchmark TerminalTextEffects effects without terminal I/O.")
    parser.add_argument("--effect", default="wipe", help="Effect command to benchmark, or 'all'.")
    parser.add_argument(
        "--input-preset",
        choices=sorted([*INPUT_PRESETS, "generated"]),
        default="medium",
        help="Input data preset to benchmark.",
    )
    parser.add_argument("--samples", type=_positive_int, default=DEFAULT_SAMPLES, help="Timed samples to run.")
    parser.add_argument("--warmups", type=_non_negative_int, default=DEFAULT_WARMUPS, help="Warmup iterations to run.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Base random seed.")
    parser.add_argument("--profile", action="store_true", help="Print cProfile output for the first selected effect.")
    parser.add_argument("--json-out", type=Path, help="Write benchmark report JSON to this path.")
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("BASELINE_JSON", "CANDIDATE_JSON"),
        type=Path,
        help="Compare two benchmark report JSON files and exit.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the benchmark command line interface."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.compare:
        baseline_report = _load_report(args.compare[0])
        candidate_report = _load_report(args.compare[1])
        print(compare_reports(baseline_report, candidate_report))
        return 0

    effect_classes = _effect_classes()
    if args.effect == "all":
        selected_effects = sorted(effect_classes.items())
    else:
        try:
            selected_effects = [(args.effect, effect_classes[args.effect])]
        except KeyError:
            parser.error(f"unknown effect: {args.effect}")

    results = [
        run_benchmark(
            effect_name=effect_name,
            effect_class=effect_class,
            input_preset=args.input_preset,
            samples=args.samples,
            warmups=args.warmups,
            seed=args.seed,
        )
        for effect_name, effect_class in selected_effects
    ]
    report = build_report(results)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2, sort_keys=True))

    if args.profile:
        effect_name, effect_class = selected_effects[0]
        print(f"\nProfile for {effect_name}/{args.input_preset}:")
        print(run_profile(effect_class, args.input_preset, args.seed))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
