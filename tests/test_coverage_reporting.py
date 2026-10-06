"""Verify honest coverage comparisons, baseline provenance, and changed-line reporting."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import zipfile
from typing import TYPE_CHECKING

import pytest

from tools import report_coverage as coverage

if TYPE_CHECKING:
    from pathlib import Path

BASE = "1" * 40


@pytest.fixture
def report() -> coverage.Report:
    """Provide separate line and branch totals and executable line classifications."""
    return {
        "meta": {"format": 3, "version": "7.11.3", "branch_coverage": True},
        "totals": {"covered_lines": 80, "num_statements": 100, "covered_branches": 6, "num_branches": 10},
        "files": {"terminaltexteffects/example.py": {"executed_lines": [1, 4], "missing_lines": [2, 3]}},
    }


@pytest.fixture
def current() -> dict[str, object]:
    """Provide a successful canonical current run with explicit compatibility metadata."""
    return {
        "profile": coverage.PROFILE,
        "platform": "linux",
        "python": "3.14",
        "selection_config": "config-digest",
        "coverage_format": 3,
        "tools": {"coverage": "7.11.3"},
        "revision": "2" * 40,
        "repository": "ChrisBuilds/terminaltexteffects",
        "event": "pull_request",
        "branch": "123/merge",
        "run_id": "100",
        "run_attempt": "1",
        "test_outcome": "success",
    }


def previous_context(current: dict[str, object]) -> dict[str, object]:
    """Return metadata for the exact successful main baseline rather than PR data."""
    return {**current, "revision": BASE, "event": "push", "branch": "main", "run_id": "42", "run_attempt": "2"}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("revision", "stale"),
        ("event", "pull_request"),
        ("branch", "feature"),
        ("test_outcome", "failure"),
        ("run_id", "other"),
        ("run_attempt", "1"),
        ("repository", "other/repo"),
        ("profile", "exhaustive"),
        ("platform", "darwin"),
        ("python", "3.13"),
        ("selection_config", "other"),
        ("coverage_format", 2),
        ("tools", {"coverage": "different"}),
    ],
)
def test_incompatible_or_unsuccessful_baselines_are_rejected(
    current: dict[str, object], field: str, value: object
) -> None:
    """Do not present misleading deltas after provenance, scope or tools change."""
    previous = previous_context(current)
    previous[field] = value
    with pytest.raises(coverage.BaselineUnavailableError):
        coverage.verify_baseline(current, previous, BASE, 42, 2)


@pytest.mark.parametrize("field", ["test_outcome", "platform", "python"])
def test_noncanonical_current_runs_cannot_compare(current: dict[str, object], field: str) -> None:
    """Failed, local or differently instrumented reports are diagnostic only."""
    current[field] = "wrong"
    previous = previous_context(current)
    with pytest.raises(coverage.BaselineUnavailableError):
        coverage.verify_baseline(current, previous, BASE, 42, 2)


def test_summary_separates_metrics_denominators_and_changed_lines(
    report: coverage.Report, current: dict[str, object]
) -> None:
    """A line improvement and branch drop remain distinct; excluded lines do not count."""
    baseline: coverage.Report = {
        **report,
        "totals": {"covered_lines": 70, "num_statements": 100, "covered_branches": 8, "num_branches": 10},
    }
    text = coverage.summary(
        report, current, baseline, BASE, "", "https://example.com/run", {"terminaltexteffects/example.py": {2, 4, 99}}
    )
    assert "| Lines | 70/100 | 70.00% | 80/100 | 80.00% | +10.00 |" in text
    assert "| Branches | 8/10 | 80.00% | 6/10 | 60.00% | -20.00 |" in text
    assert "1/2 exercised; 1 untested" in text
    assert "untested changed lines 2." in text
    assert "\n| Lines" in text  # Table rows must not be separated by blank paragraphs.
    assert "no percentage gate" in text


def archive_bytes(report: coverage.Report, metadata: dict[str, object] | None) -> bytes:
    """Create JSON artifacts without writing or extracting archive paths."""
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("coverage.json", json.dumps(report))
        if metadata is not None:
            archive.writestr("context.json", json.dumps(metadata))
        archive.writestr("../must-not-extract", "untrusted member")
    return stream.getvalue()


@pytest.mark.parametrize("fault", ["none", "wrong-sha", "failed-run", "expired", "missing-context", "bad-zip"])
def test_fetch_requires_exact_successful_main_artifact(
    report: coverage.Report,
    current: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    """Filter actual run/artifact data again and never execute/extract downloaded artifacts."""
    run = {
        "id": 42,
        "run_attempt": 2,
        "head_sha": BASE,
        "head_branch": "main",
        "event": "push",
        "status": "completed",
        "conclusion": "success",
    }
    if fault == "wrong-sha":
        run["head_sha"] = "stale"
    if fault == "failed-run":
        run["conclusion"] = "failure"
    metadata = None if fault == "missing-context" else previous_context(current)
    payload = b"not a zip" if fault == "bad-zip" else archive_bytes(report, metadata)
    endpoints: list[str] = []

    def fake_api(endpoint: str) -> bytes:
        endpoints.append(endpoint)
        if "/workflows/" in endpoint:
            return json.dumps({"workflow_runs": [run]}).encode()
        if "/runs/" in endpoint:
            return json.dumps(
                {"artifacts": [{"id": 5, "name": coverage.ARTIFACT, "expired": fault == "expired"}]}
            ).encode()
        return payload

    monkeypatch.setattr(coverage, "api", fake_api)
    if fault == "none":
        baseline, url = coverage.fetch_baseline(current, BASE)
        assert baseline == report
        assert url.endswith("/actions/runs/42")
    else:
        with pytest.raises((coverage.BaselineUnavailableError, zipfile.BadZipFile)):
            coverage.fetch_baseline(current, BASE)
    assert f"head_sha={BASE}" in endpoints[0]


@pytest.mark.parametrize("outcome", ["success", "failure"])
def test_missing_baseline_is_informational_and_keeps_current_artifact(
    tmp_path: Path,
    report: coverage.Report,
    current: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    outcome: str,
) -> None:
    """API outages and failed tests cannot create a baseline or erase useful current totals."""
    path = tmp_path / "coverage.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["report", "--report", str(path), "--base", BASE, "--test-outcome", outcome])
    monkeypatch.setattr(coverage, "context", lambda *_: {**current, "test_outcome": outcome})
    monkeypatch.setattr(coverage, "changed_lines", lambda *_: {"terminaltexteffects/example.py": {2}})

    def unavailable(*_args: object) -> bytes:
        assert outcome == "success", "Failed tests must not fetch a baseline"
        command = "gh"
        raise subprocess.TimeoutExpired(command, 20)

    monkeypatch.setattr(coverage, "api", unavailable)
    assert coverage.main() == 0
    text = capsys.readouterr().out
    assert "Baseline unavailable" in text
    assert "80/100" in text
    assert "untested changed lines 2" in text
    assert json.loads(path.with_name("context.json").read_text())["test_outcome"] == outcome


@pytest.mark.parametrize("fault", ["branch", "scope", "zero-total", "impossible-count"])
def test_invalid_current_collection_fails(report: coverage.Report, fault: str) -> None:
    """Broken current coverage still fails instead of being hidden as an optional comparison."""
    if fault == "branch":
        report["meta"]["branch_coverage"] = False
    elif fault == "scope":
        report["files"] = {"tests/example.py": {"executed_lines": [], "missing_lines": []}}
    elif fault == "zero-total":
        report["totals"]["num_branches"] = 0
    else:
        report["totals"]["covered_lines"] = 101
    with pytest.raises(ValueError, match=r"coverage|Coverage"):
        coverage.validate_report(report)


def test_git_hunks_include_new_modified_renamed_lines_only(tmp_path: Path) -> None:
    """Real Git selection handles deletion, comments, spaced names, and rename destinations."""

    def git(*args: str) -> str:
        return coverage.git(tmp_path, *args).decode().strip()

    git("init", "-b", "main")
    git("config", "user.name", "Coverage Test")
    git("config", "user.email", "test@example.com")
    package = tmp_path / "terminaltexteffects"
    package.mkdir()
    (package / "example.py").write_text("VALUE = 1\nKEEP = 2\n", encoding="utf-8")
    (package / "deleted.py").write_text("DELETE = 1\n", encoding="utf-8")
    (package / "renamed.py").write_text("OLD = 1\n", encoding="utf-8")
    git("add", ".")
    git("commit", "--no-verify", "-m", "Baseline")
    base = git("rev-parse", "HEAD")
    (package / "example.py").write_text("VALUE = 3\nKEEP = 2\n# comment\nADDED = 4\n", encoding="utf-8")
    git("rm", "terminaltexteffects/deleted.py")
    git("mv", "terminaltexteffects/renamed.py", "terminaltexteffects/with spaces.py")
    (tmp_path / "notes.py").write_text("TOOL = 1\n", encoding="utf-8")
    git("add", ".")
    git("commit", "--no-verify", "-m", "Changes")
    assert coverage.changed_lines(tmp_path, base) == {
        "terminaltexteffects/example.py": {1, 3, 4},
        "terminaltexteffects/with spaces.py": {1},
    }


def test_unavailable_diff_does_not_claim_no_changed_lines(report: coverage.Report, current: dict[str, object]) -> None:
    """A failed source diff is unknown rather than proof that no code changed."""
    text = coverage.summary(report, current, None, BASE, "diff unavailable", "", None)
    assert "Changed-line analysis unavailable" in text
    assert "No added/modified runtime Python lines" not in text


def test_changed_unmeasured_files_are_visible(report: coverage.Report, current: dict[str, object]) -> None:
    """Files omitted from collection cannot be silently treated as covered."""
    text = coverage.summary(report, current, None, BASE, "missing baseline", "", {"terminaltexteffects/new.py": {1}})
    assert "new.py`" in text
    assert "changed file absent from coverage report" in text


def test_context_tracks_measurement_changes_without_unrelated_settings(
    tmp_path: Path,
    report: coverage.Report,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Changing test selection invalidates comparison; unrelated project settings do not."""
    for name in (
        "COVERAGE_REVISION",
        "GITHUB_REPOSITORY",
        "GITHUB_EVENT_NAME",
        "GITHUB_REF_NAME",
        "GITHUB_RUN_ID",
        "GITHUB_RUN_ATTEMPT",
    ):
        monkeypatch.setenv(name, "fixture")
    (tmp_path / "tests").mkdir()
    workflow = tmp_path / ".github/workflows/ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("# default CI collection\n", encoding="utf-8")
    for name in ("conftest.py", "pairwise.py"):
        (tmp_path / "tests" / name).write_text("# selection\n", encoding="utf-8")
    config = tmp_path / "pyproject.toml"
    text = (
        '[tool.pytest.ini_options]\naddopts = ["-m", "not visual"]\n'
        '[tool.coverage.run]\nbranch = true\n[tool.pyright]\npythonVersion = "3.9"\n'
    )
    config.write_text(text, encoding="utf-8")
    original = coverage.context(tmp_path, report, "success")
    config.write_text(text.replace('"3.9"', '"3.10"'), encoding="utf-8")
    assert coverage.context(tmp_path, report, "success")["selection_config"] == original["selection_config"]
    config.write_text(text.replace("not visual", "not visual and not manual"), encoding="utf-8")
    assert coverage.context(tmp_path, report, "success")["selection_config"] != original["selection_config"]
    assert original["test_outcome"] == "success"
    assert "GH_TOKEN" not in original
    config.write_text(text, encoding="utf-8")
    workflow.write_text("# changed CI collection\n", encoding="utf-8")
    assert coverage.context(tmp_path, report, "success")["selection_config"] != original["selection_config"]


def test_two_commit_checkout_can_read_exact_merge_base(tmp_path: Path) -> None:
    """Coverage can inspect a tested merge's immediate base without fetching all history."""
    source, clone = tmp_path / "source", tmp_path / "clone"
    source.mkdir()

    def git(*args: str) -> str:
        return coverage.git(source, *args).decode().strip()

    git("init", "-b", "main")
    git("config", "user.name", "Coverage Test")
    git("config", "user.email", "test@example.com")
    package = source / "terminaltexteffects"
    package.mkdir()
    example = package / "example.py"
    example.write_text("VALUE = 1\n", encoding="utf-8")
    git("add", ".")
    git("commit", "--no-verify", "-m", "Base")
    base = git("rev-parse", "HEAD")
    git("checkout", "-b", "feature")
    example.write_text("VALUE = 2\n", encoding="utf-8")
    git("commit", "--no-verify", "-am", "Change")
    git("checkout", "main")
    git("merge", "--no-ff", "feature", "-m", "Tested merge")
    coverage.git(tmp_path, "clone", "--quiet", "--depth", "2", source.as_uri(), str(clone))
    assert coverage.git(clone, "rev-parse", "--is-shallow-repository").strip() == b"true"
    assert coverage.changed_lines(clone, base) == {"terminaltexteffects/example.py": {1}}
