"""Tests for the stdlib performance benchmark harness."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

from terminaltexteffects.effects.effect_wipe import Wipe
from tools.perf import benchmark_effects

if TYPE_CHECKING:
    from pathlib import Path


def _report(effect: str, render_mean: float, lifecycle: str = "iterator") -> dict[str, Any]:
    """Build a minimal benchmark report for comparison tests."""
    return {
        "schema_version": 2,
        "results": [
            {
                "effect": effect,
                "input_preset": "small",
                "lifecycle": lifecycle,
                "summary": {
                    "build_seconds": {"mean": 1.0},
                    "render_seconds": {"mean": render_mean},
                    "total_seconds": {"mean": 3.0},
                    "frames": 10,
                    "output_characters": 500,
                },
            },
        ],
    }


def test_run_benchmark_returns_stable_summary_keys() -> None:
    """A benchmark run should expose stable machine-readable summary keys."""
    result = benchmark_effects.run_benchmark(
        effect_name="wipe",
        effect_class=Wipe,
        input_preset="small",
        samples=1,
        warmups=0,
        seed=123,
    )

    assert result["effect"] == "wipe"
    assert result["input_preset"] == "small"
    assert result["lifecycle"] == "iterator"
    assert result["samples"] == 1
    assert result["warmups"] == 0
    summary = result["summary"]
    assert set(summary) == {
        "build_seconds",
        "render_seconds",
        "total_seconds",
        "frames",
        "output_characters",
        "frame_counts",
        "output_character_counts",
    }
    assert summary["frames"] > 0
    assert summary["output_characters"] > 0
    assert summary["build_seconds"]["mean"] >= 0
    assert summary["render_seconds"]["mean"] >= 0
    assert summary["total_seconds"]["mean"] >= summary["render_seconds"]["mean"]


def test_run_benchmark_supports_terminal_output_lifecycle() -> None:
    """The end-to-end mode should exercise the output context without writing to stdout."""
    result = benchmark_effects.run_benchmark(
        effect_name="wipe",
        effect_class=Wipe,
        input_preset="small",
        samples=1,
        warmups=0,
        seed=123,
        lifecycle="terminal-output",
    )

    assert result["lifecycle"] == "terminal-output"
    assert result["summary"]["frames"] > 0
    assert result["summary"]["output_characters"] > 0


def test_run_iteration_rejects_unknown_lifecycle() -> None:
    """Direct harness callers receive a clear error for unsupported lifecycle modes."""
    with pytest.raises(ValueError, match="Unknown benchmark lifecycle"):
        benchmark_effects.run_iteration(Wipe, "A", 123, "unknown")  # type: ignore[arg-type]


def test_compare_reports_prints_percent_deltas() -> None:
    """Report comparison should include advisory percent deltas for timed metrics."""
    baseline = _report("wipe", render_mean=2.0)
    candidate = _report("wipe", render_mean=1.5)

    comparison = benchmark_effects.compare_reports(baseline, candidate)

    assert "effect,input,lifecycle,metric,baseline,candidate,delta_percent" in comparison
    assert "wipe,small,iterator,render_seconds,2.000000000,1.500000000,-25.00" in comparison
    assert "wipe,small,iterator,frames,10,10,0" in comparison
    assert "wipe,small,iterator,output_characters,500,500,0" in comparison


def test_compare_reports_keeps_lifecycles_separate() -> None:
    """Iterator-only and end-to-end scenarios must not be compared to each other."""
    baseline = _report("wipe", render_mean=2.0, lifecycle="terminal-output")
    candidate = _report("wipe", render_mean=1.5, lifecycle="iterator")

    comparison = benchmark_effects.compare_reports(baseline, candidate)

    assert "wipe,small,terminal-output,missing_candidate" in comparison


def test_main_writes_json_report(tmp_path: Path) -> None:
    """The CLI entry point should write a valid benchmark JSON report."""
    output_path = tmp_path / "benchmark.json"

    exit_code = benchmark_effects.main(
        [
            "--effect",
            "wipe",
            "--input-preset",
            "small",
            "--samples",
            "1",
            "--warmups",
            "0",
            "--lifecycle",
            "terminal-output",
            "--json-out",
            str(output_path),
        ],
    )

    assert exit_code == 0
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["schema_version"] == 2
    assert report["tool"] == "tools/perf/benchmark_effects.py"
    assert report["results"][0]["effect"] == "wipe"
    assert report["results"][0]["lifecycle"] == "terminal-output"
