"""Tests for the sampling-profiler JSONL summary tool."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

from tools.perf import summarize_profile

if TYPE_CHECKING:
    from pathlib import Path


def _records(*, end: bool = True, version: int = 0) -> list[dict[str, Any]]:
    """Build a small JSONL export with one recursive function and one GC frame."""
    run = {"v": version, "run_id": "abc"}
    records: list[dict[str, Any]] = [
        {"type": "meta", **run, "sample_interval_usec": 1000, "mode": "wall"},
        {
            "type": "string_table",
            **run,
            "strings": [
                {"str_id": 0, "value": str(summarize_profile.REPO_ROOT / "terminaltexteffects/engine/terminal.py")},
                {"str_id": 1, "value": "Terminal.render"},
                {"str_id": 2, "value": "/venv/lib/python3.15/site-packages/terminaltexteffects/engine/motion.py"},
                {"str_id": 3, "value": "Path.step|inner"},
                {"str_id": 4, "value": "~"},
                {"str_id": 5, "value": "<GC>"},
            ],
        },
        {
            "type": "frame_table",
            **run,
            "frames": [
                {"frame_id": 0, "path_str_id": 0, "func_str_id": 1, "line": 10},
                {"frame_id": 1, "path_str_id": 0, "func_str_id": 1, "line": 12},
                {"frame_id": 2, "path_str_id": 2, "func_str_id": 3, "line": 5},
                {"frame_id": 3, "path_str_id": 4, "func_str_id": 5, "line": 0},
            ],
        },
        {
            "type": "agg",
            **run,
            "kind": "frame",
            "scope": "final",
            "samples_total": 10,
            "entries": [
                {"frame_id": 0, "self": 3, "cumulative": 9},
                {"frame_id": 1, "self": 2, "cumulative": 2},
                {"frame_id": 2, "self": 4, "cumulative": 4},
                {"frame_id": 3, "self": 1, "cumulative": 1},
            ],
        },
    ]
    if end:
        records.append({"type": "end", **run, "samples_total": 10})
    return records


def _write(path: Path, records: list[dict[str, Any]]) -> Path:
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
    return path


def test_load_profile_aggregates_self_samples(tmp_path: Path) -> None:
    """Lines of one function should sum, and paths should be shortened."""
    summary = summarize_profile.load_profile(_write(tmp_path / "p.jsonl", _records()))

    assert summary.total_samples == 10
    assert summary.sample_interval_usec == 1000
    assert summary.by_function.most_common() == [
        (("terminaltexteffects/engine/terminal.py", "Terminal.render"), 5),
        (("terminaltexteffects/engine/motion.py", "Path.step|inner"), 4),
        (("(synthetic)", "<GC>"), 1),
    ]
    assert summary.by_line["terminaltexteffects/engine/terminal.py", "Terminal.render", 12] == 2
    assert summary.by_file["terminaltexteffects/engine/terminal.py"] == 5


def test_render_markdown_escapes_table_cells(tmp_path: Path) -> None:
    """Rendered tables should report percentages, escape pipes, and respect the row limit."""
    summary = summarize_profile.load_profile(_write(tmp_path / "p.jsonl", _records()))

    markdown = summarize_profile.render_markdown(summary, title="all / medium", limit=2)

    assert markdown.startswith("### all / medium\n\n10 samples, 1,000 Hz, wall mode.")
    assert "| 50.0% | 5 | `Terminal.render` | `terminaltexteffects/engine/terminal.py` |" in markdown
    assert "`Path.step\\|inner`" in markdown
    assert "<GC>" not in markdown


@pytest.mark.parametrize(
    ("records", "message"),
    [
        (_records(end=False), "missing end record"),
        (_records(version=1), "unsupported record version 1"),
    ],
)
def test_load_profile_rejects_unusable_exports(tmp_path: Path, records: list[dict[str, Any]], message: str) -> None:
    """Truncated exports and unknown schema versions should fail clearly."""
    with pytest.raises(ValueError, match=message):
        summarize_profile.load_profile(_write(tmp_path / "p.jsonl", records))


def test_main_writes_output_file(tmp_path: Path) -> None:
    """The CLI should write Markdown to the requested file."""
    source = _write(tmp_path / "p.jsonl", _records())
    output = tmp_path / "out" / "summary.md"

    assert summarize_profile.main([str(source), "--title", "Scenario", "-o", str(output)]) == 0
    assert output.read_text(encoding="utf-8").startswith("### Scenario\n")
