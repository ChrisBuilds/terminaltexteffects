"""Summarize a Python 3.15 sampling-profiler JSONL export as Markdown.

`python -m profiling.sampling` (Python 3.15+) writes interactive HTML reports, but CI job summaries
and pull request descriptions need plain text. This script reads the `--jsonl` export and prints
Markdown tables of the hottest functions, lines, and files by self samples. It uses only the
standard library and runs on any supported Python version, so the export can be summarized
anywhere.
"""

from __future__ import annotations

import argparse
import json
import sys
import sysconfig
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

SUPPORTED_RECORD_VERSION = 0
DEFAULT_LIMIT = 20
REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Frame:
    """One source location recorded by the sampling profiler."""

    path: str
    function: str
    line: int


@dataclass(frozen=True)
class ProfileSummary:
    """Self-sample counts aggregated from one JSONL profile."""

    total_samples: int
    sample_interval_usec: int | None
    mode: str | None
    by_function: Counter[tuple[str, str]]
    by_line: Counter[tuple[str, str, int]]
    by_file: Counter[str]


def _shorten_path(path: str, prefixes: Sequence[tuple[str, str]]) -> str:
    """Return `path` relative to the first matching root, labelled for readability."""
    for prefix, label in prefixes:
        if prefix and path.startswith(prefix):
            return label + path[len(prefix) :].lstrip("/")
    return path


def _path_prefixes(extra_roots: Iterable[Path]) -> list[tuple[str, str]]:
    """Build path prefixes to strip, most specific first."""
    prefixes = [(str(root.resolve()) + "/", "") for root in extra_roots]
    prefixes.append((str(REPO_ROOT) + "/", ""))
    for key in ("stdlib", "platstdlib"):
        location = sysconfig.get_paths().get(key)
        if location:
            prefixes.append((location.rstrip("/") + "/", "<stdlib>/"))
    return sorted(prefixes, key=lambda item: len(item[0]), reverse=True)


def _site_packages_prefix(path: str) -> str:
    """Strip any virtualenv or interpreter prefix up to `site-packages/`."""
    marker = "/site-packages/"
    index = path.find(marker)
    return path[index + len(marker) :] if index != -1 else path


def load_profile(path: Path, *, extra_roots: Iterable[Path] = ()) -> ProfileSummary:
    """Aggregate self samples from a `profiling.sampling --jsonl` export."""
    prefixes = _path_prefixes(extra_roots)
    strings: dict[int, str] = {}
    frames: dict[int, Frame] = {}
    by_function: Counter[tuple[str, str]] = Counter()
    by_line: Counter[tuple[str, str, int]] = Counter()
    by_file: Counter[str] = Counter()
    total_samples: int | None = None
    sample_interval_usec: int | None = None
    mode: str | None = None

    with path.open(encoding="utf-8") as stream:
        for line_number, raw_line in enumerate(stream, start=1):
            if not raw_line.strip():
                continue
            record: dict[str, Any] = json.loads(raw_line)
            version = record.get("v")
            if version != SUPPORTED_RECORD_VERSION:
                msg = f"{path}:{line_number}: unsupported record version {version!r}"
                raise ValueError(msg)
            record_type = record.get("type")
            if record_type == "meta":
                sample_interval_usec = record.get("sample_interval_usec")
                mode = record.get("mode")
            elif record_type == "string_table":
                strings.update((entry["str_id"], entry["value"]) for entry in record["strings"])
            elif record_type == "frame_table":
                for entry in record["frames"]:
                    raw_path = strings[entry["path_str_id"]]
                    # Synthetic frames such as `<GC>` and `<native>` have no file.
                    shortened = (
                        "(synthetic)" if raw_path == "~" else _site_packages_prefix(_shorten_path(raw_path, prefixes))
                    )
                    frames[entry["frame_id"]] = Frame(shortened, strings[entry["func_str_id"]], entry["line"])
            elif record_type == "agg" and record.get("kind") == "frame" and record.get("scope") == "final":
                for entry in record["entries"]:
                    self_samples = entry["self"]
                    if not self_samples:
                        continue
                    frame = frames[entry["frame_id"]]
                    by_function[frame.path, frame.function] += self_samples
                    by_line[frame.path, frame.function, frame.line] += self_samples
                    by_file[frame.path] += self_samples
            elif record_type == "end":
                total_samples = record["samples_total"]

    if total_samples is None:
        msg = f"{path}: missing end record; the export may be truncated"
        raise ValueError(msg)
    return ProfileSummary(total_samples, sample_interval_usec, mode, by_function, by_line, by_file)


def _percent(samples: int, total: int) -> str:
    return f"{100 * samples / total:.1f}%" if total else "n/a"


def _escape(text: str) -> str:
    return text.replace("|", "\\|")


def _table(headers: Sequence[str], rows: Iterable[Sequence[str]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def render_markdown(summary: ProfileSummary, *, title: str, limit: int = DEFAULT_LIMIT) -> str:
    """Render self-sample hotspots as Markdown."""
    total = summary.total_samples
    details = [f"{total:,} samples"]
    if summary.sample_interval_usec:
        details.append(f"{1_000_000 / summary.sample_interval_usec:,.0f} Hz")
    if summary.mode:
        details.append(f"{summary.mode} mode")
    lines = [f"### {_escape(title)}", "", ", ".join(details) + ". Self samples: time spent in the frame itself.", ""]

    lines.append(f"**Functions** (top {limit})")
    lines.append("")
    lines.extend(
        _table(
            ("Self", "Samples", "Function", "File"),
            (
                (_percent(samples, total), f"{samples:,}", f"`{_escape(function)}`", f"`{_escape(path)}`")
                for (path, function), samples in summary.by_function.most_common(limit)
            ),
        ),
    )
    lines.extend(["", f"**Lines** (top {limit})", ""])
    lines.extend(
        _table(
            ("Self", "Samples", "Location", "Function"),
            (
                (_percent(samples, total), f"{samples:,}", f"`{_escape(path)}:{line}`", f"`{_escape(function)}`")
                for (path, function, line), samples in summary.by_line.most_common(limit)
            ),
        ),
    )
    lines.extend(["", f"**Files** (top {limit})", ""])
    lines.extend(
        _table(
            ("Self", "Samples", "File"),
            (
                (_percent(samples, total), f"{samples:,}", f"`{_escape(path)}`")
                for path, samples in summary.by_file.most_common(limit)
            ),
        ),
    )
    return "\n".join(lines) + "\n"


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        msg = "must be at least 1"
        raise argparse.ArgumentTypeError(msg)
    return parsed


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""
    parser = argparse.ArgumentParser(description="Summarize a sampling-profiler JSONL export as Markdown.")
    parser.add_argument("jsonl", type=Path, help="Profile exported with `profiling.sampling --jsonl`.")
    parser.add_argument("--title", help="Heading for the report. Defaults to the file name.")
    parser.add_argument("--limit", type=_positive_int, default=DEFAULT_LIMIT, help="Rows per table.")
    parser.add_argument(
        "--root",
        type=Path,
        action="append",
        default=[],
        help="Extra directory to strip from file paths, such as a baseline checkout. Repeatable.",
    )
    parser.add_argument("-o", "--output", type=Path, help="Write Markdown here instead of standard output.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line interface."""
    args = build_arg_parser().parse_args(argv)
    summary = load_profile(args.jsonl, extra_roots=args.root)
    markdown = render_markdown(summary, title=args.title or args.jsonl.name, limit=args.limit)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown, encoding="utf-8")
    else:
        sys.stdout.write(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
