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
        "schema_version": 3,
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
    assert result["measure_memory"] is False
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
        "build_peak_memory_bytes",
        "peak_memory_bytes",
    }
    assert summary["frames"] > 0
    assert summary["output_characters"] > 0
    assert summary["build_seconds"]["mean"] >= 0
    assert summary["render_seconds"]["mean"] >= 0
    assert summary["total_seconds"]["mean"] >= summary["render_seconds"]["mean"]
    assert summary["build_peak_memory_bytes"] is None
    assert summary["peak_memory_bytes"] is None


def test_run_benchmark_measures_peak_memory() -> None:
    """Memory-enabled runs should report build and complete-iteration peaks."""
    result = benchmark_effects.run_benchmark(
        effect_name="wipe",
        effect_class=Wipe,
        input_preset="sparse",
        samples=1,
        warmups=0,
        seed=123,
        measure_memory=True,
    )

    assert result["measure_memory"] is True
    assert result["summary"]["build_peak_memory_bytes"]["mean"] > 0
    assert result["summary"]["peak_memory_bytes"]["mean"] > 0


def test_unicode_input_preset_contains_double_cell_symbols() -> None:
    """The Unicode preset should exercise true double-cell rendering."""
    input_data = benchmark_effects._make_input_data("unicode")

    assert "界" in input_data
    assert "😀" in input_data


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
            "--memory",
            "--json-out",
            str(output_path),
        ],
    )

    assert exit_code == 0
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["schema_version"] == 3
    assert report["tool"] == "tools/perf/benchmark_effects.py"
    assert report["results"][0]["effect"] == "wipe"
    assert report["results"][0]["lifecycle"] == "terminal-output"
    assert report["results"][0]["measure_memory"] is True


@pytest.mark.parametrize(
    ("effect", "effect_args", "field", "expected"),
    [
        ("matrix", [], "rain_time", 1),
        ("thunderstorm", [], "storm_time", 1),
        ("colorshift", [], "cycles", 2),
        ("matrix", ["--rain-time", "5"], "rain_time", 5),
        ("matrix", ["--rain-t", "5"], "rain_time", 5),
        ("colorshift", ["--cycles=4"], "cycles", 4),
    ],
)
def test_build_configs_shortens_hold_phases_unless_set(
    effect: str,
    effect_args: list[str],
    field: str,
    expected: float,
) -> None:
    """Explicit effect options, including abbreviations, should win over harness shortening."""
    effect_config, terminal_config = benchmark_effects.build_configs(effect, effect_args)

    assert getattr(effect_config, field) == expected
    assert terminal_config.frame_rate == 0


def test_build_configs_applies_terminal_args() -> None:
    """Terminal options should be parsed exactly as `tte` parses them."""
    _, terminal_config = benchmark_effects.build_configs(
        "wipe",
        terminal_args=["--xterm-colors", "--existing-color-handling", "dynamic", "--canvas-width", "-1"],
    )

    assert terminal_config.xterm_colors is True
    assert terminal_config.existing_color_handling == "dynamic"


@pytest.mark.parametrize("terminal_args", [["--frame-rate", "60"], ["--record", "out.tterec"], ["--seed=1"]])
def test_build_configs_rejects_non_terminal_args(terminal_args: list[str]) -> None:
    """Only terminal configuration options other than the frame rate are accepted."""
    with pytest.raises(ValueError, match="unsupported terminal argument"):
        benchmark_effects.build_configs("wipe", terminal_args=terminal_args)


def test_build_configs_reports_invalid_effect_args_like_tte(capsys: pytest.CaptureFixture[str]) -> None:
    """Invalid effect options should fail through the `tte` parser's usage error."""
    with pytest.raises(SystemExit) as exit_info:
        benchmark_effects.build_configs("wipe", ["--no-such-option"])

    assert exit_info.value.code == 2
    assert "unrecognized arguments: --no-such-option" in capsys.readouterr().err


def test_build_configs_rejects_unknown_effect() -> None:
    """Direct callers receive a clear error for unknown effects."""
    with pytest.raises(ValueError, match="unknown effect"):
        benchmark_effects.build_configs("nosucheffect")


def test_run_benchmark_records_and_applies_cli_args() -> None:
    """Reports should record the arguments that produced them, and the arguments should take effect."""
    default = benchmark_effects.run_benchmark(
        effect_name="wipe",
        effect_class=Wipe,
        input_preset="small",
        samples=1,
        warmups=0,
        seed=123,
    )
    configured = benchmark_effects.run_benchmark(
        effect_name="wipe",
        effect_class=Wipe,
        input_preset="small",
        samples=1,
        warmups=0,
        seed=123,
        effect_args=["--wipe-delay", "4"],
        terminal_args=["--no-color"],
    )

    assert default["effect_args"] == []
    assert configured["effect_args"] == ["--wipe-delay", "4"]
    assert configured["terminal_args"] == ["--no-color"]
    assert configured["summary"]["frames"] != default["summary"]["frames"]


def test_main_rejects_effect_args_for_all_effects(capsys: pytest.CaptureFixture[str]) -> None:
    """Effect options differ between effects, so they need a single effect."""
    with pytest.raises(SystemExit):
        benchmark_effects.main(["--effect", "all", "--effect-args", "--wipe-delay 4"])

    assert "--effect-args requires a single --effect" in capsys.readouterr().err


def test_main_rejects_non_terminal_args(capsys: pytest.CaptureFixture[str]) -> None:
    """Unsupported terminal options should fail before any benchmark runs."""
    with pytest.raises(SystemExit):
        benchmark_effects.main(["--effect", "wipe", "--terminal-args", "--frame-rate 60"])

    assert "unsupported terminal argument '--frame-rate'" in capsys.readouterr().err


def test_main_accepts_single_option_args_with_equals(tmp_path: Path) -> None:
    """A lone option value needs the `=` form, which the workflow and docs use."""
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
            "--effect-args=--reverse-wipe-direction",
            "--terminal-args=--no-color",
            "--json-out",
            str(output_path),
        ],
    )

    assert exit_code == 0
    result = json.loads(output_path.read_text(encoding="utf-8"))["results"][0]
    assert result["effect_args"] == ["--reverse-wipe-direction"]
    assert result["terminal_args"] == ["--no-color"]
