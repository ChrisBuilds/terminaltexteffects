"""Report informational coverage changes using an exact, successful main CI baseline."""

from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import os
import re
import subprocess
import sys
import zipfile
from importlib.metadata import version
from pathlib import Path, PurePosixPath
from typing import TypedDict

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

PROFILE = "linux-python3.14-default-pairwise-v1"
ARTIFACT = "coverage-python-3.14"


class Counts(TypedDict):
    """Represent separate statement and branch counters from coverage.py."""

    covered_lines: int
    num_statements: int
    covered_branches: int
    num_branches: int


class FileReport(TypedDict):
    """Describe executable source lines in one measured file."""

    executed_lines: list[int]
    missing_lines: list[int]


class Report(TypedDict):
    """Describe the subset of coverage.py JSON used by this report."""

    meta: dict[str, object]
    totals: Counts
    files: dict[str, FileReport]


class BaselineUnavailableError(ValueError):
    """Signal an optional comparison that cannot be trusted or retrieved."""


def validate_report(report: Report) -> None:
    """Reject invalid package reports rather than display invented percentages."""
    if not isinstance(report, dict) or any(
        not isinstance(report.get(key), dict) for key in ("meta", "totals", "files")
    ):
        message = "Invalid coverage report structure"
        raise ValueError(message)
    if report["meta"]["branch_coverage"] is not True or not report["files"]:
        message = "Missing package branch coverage"
        raise ValueError(message)
    for name, measured in report["files"].items():
        path = PurePosixPath(name)
        if not name.startswith("terminaltexteffects/") or ".." in path.parts:
            message = "Coverage must measure the runtime package only"
            raise ValueError(message)
        for key in ("executed_lines", "missing_lines"):
            if any(type(line) is not int or line <= 0 for line in measured[key]):
                message = "Invalid executable line numbers"
                raise ValueError(message)
    totals = report["totals"]
    for covered, total in (("covered_lines", "num_statements"), ("covered_branches", "num_branches")):
        numerator, denominator = totals[covered], totals[total]
        if (
            type(numerator) is not int
            or type(denominator) is not int
            or not 0 <= numerator <= denominator
            or denominator == 0
        ):
            message = "Invalid or empty coverage totals"
            raise ValueError(message)


def context(root: Path, report: Report, outcome: str) -> dict[str, object]:
    """Record scope, selection, tools and provenance for later baseline validation."""
    configuration = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["tool"]
    selected = {key: configuration[key] for key in ("coverage", "pytest")}
    digest = hashlib.sha256(json.dumps(selected, sort_keys=True).encode())
    for name in ("tests/conftest.py", "tests/pairwise.py"):
        digest.update((root / name).read_bytes())
    return {
        "profile": PROFILE,
        "platform": sys.platform,
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "selection_config": digest.hexdigest(),
        "coverage_format": report["meta"]["format"],
        "tools": {name: version(name) for name in ("coverage", "pytest-cov", "pytest", "pytest-xdist")},
        "revision": os.environ["COVERAGE_REVISION"],
        "repository": os.environ["GITHUB_REPOSITORY"],
        "event": os.environ["GITHUB_EVENT_NAME"],
        "branch": os.environ["GITHUB_REF_NAME"],
        "run_id": os.environ["GITHUB_RUN_ID"],
        "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
        "test_outcome": outcome,
    }


def api(endpoint: str) -> bytes:
    """Read GitHub with bounded requests and no token in command arguments or output."""
    result = subprocess.run(  # noqa: S603 - Fixed API path components, no shell.
        ["gh", "api", endpoint],  # noqa: S607 - GitHub CLI is available on hosted Ubuntu.
        capture_output=True,
        check=False,
        timeout=20,
    )
    if result.returncode:
        message = "GitHub artifact lookup/download failed"
        raise BaselineUnavailableError(message)
    return result.stdout


def verify_baseline(
    current: dict[str, object], previous: dict[str, object], base: str, run_id: int, attempt: int
) -> None:
    """Require successful main provenance and matching measurement configuration."""
    if not isinstance(previous, dict):
        message = "Invalid baseline context structure"
        raise BaselineUnavailableError(message)
    expected = {
        "revision": base,
        "repository": current["repository"],
        "event": "push",
        "branch": "main",
        "test_outcome": "success",
        "run_id": str(run_id),
        "run_attempt": str(attempt),
    }
    if any(previous.get(key) != value for key, value in expected.items()):
        message = "Baseline provenance or test outcome does not match successful main CI"
        raise BaselineUnavailableError(message)
    for key in ("profile", "platform", "python", "selection_config", "coverage_format", "tools"):
        if previous.get(key) != current[key]:
            message = f"Baseline measurement settings differ: {key}"
            raise BaselineUnavailableError(message)
    if current["test_outcome"] != "success" or current["platform"] != "linux" or current["python"] != "3.14":
        message = "Current run is not a successful canonical Linux/Python 3.14 measurement"
        raise BaselineUnavailableError(message)


def fetch_baseline(current: dict[str, object], base: str) -> tuple[Report, str]:
    """Find a successful push on the exact base SHA and read only the two JSON members."""
    repository = str(current["repository"])
    if re.fullmatch(r"[\w.-]+/[\w.-]+", repository) is None or re.fullmatch(r"[0-9a-f]{40}", base) is None:
        message = "No valid exact base revision was supplied"
        raise BaselineUnavailableError(message)
    runs = json.loads(
        api(
            f"repos/{repository}/actions/workflows/ci.yml/runs?branch=main&event=push&status=success&head_sha={base}&per_page=10"
        )
    )["workflow_runs"]
    run = next(
        (
            r
            for r in runs
            if r["head_sha"] == base
            and r["head_branch"] == "main"
            and r["event"] == "push"
            and r["status"] == "completed"
            and r["conclusion"] == "success"
        ),
        None,
    )
    if run is None:
        message = "No successful main push CI run for the exact base commit"
        raise BaselineUnavailableError(message)
    artifacts = json.loads(api(f"repos/{repository}/actions/runs/{run['id']}/artifacts?per_page=100"))["artifacts"]
    artifact = next((a for a in artifacts if a["name"] == ARTIFACT and not a["expired"]), None)
    if artifact is None:
        message = "Baseline coverage artifact is missing or expired"
        raise BaselineUnavailableError(message)
    with zipfile.ZipFile(io.BytesIO(api(f"repos/{repository}/actions/artifacts/{artifact['id']}/zip"))) as archive:
        for name in ("context.json", "coverage.json"):
            if name not in archive.namelist() or archive.getinfo(name).file_size > 20_000_000:
                message = "Baseline metadata/report is missing or too large"
                raise BaselineUnavailableError(message)
        previous = json.loads(archive.read("context.json"))
        report: Report = json.loads(archive.read("coverage.json"))
    verify_baseline(current, previous, base, run["id"], run["run_attempt"])
    validate_report(report)
    if (
        report["meta"]["format"] != previous["coverage_format"]
        or report["meta"]["version"] != previous["tools"]["coverage"]
    ):
        message = "Baseline coverage metadata contradicts its context"
        raise BaselineUnavailableError(message)
    return report, f"https://github.com/{repository}/actions/runs/{run['id']}"


def git(root: Path, *args: str) -> bytes:
    """Read source differences without executing custom diff helpers."""
    return subprocess.run(  # noqa: S603 - Revisions and filenames are separate arguments.
        ["git", *args],  # noqa: S607 - Use the runner Git installation.
        cwd=root,
        capture_output=True,
        check=True,
        timeout=20,
    ).stdout


def changed_lines(root: Path, base: str) -> dict[str, set[int]]:
    """Return added/modified line ranges, including new files and rename destinations."""
    ancestor = git(root, "merge-base", base, "HEAD").decode().strip()
    paths = git(
        root,
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        "--no-renames",
        "--name-only",
        "--diff-filter=ACMR",
        "-z",
        ancestor,
        "HEAD",
        "--",
        "terminaltexteffects",
    )
    result: dict[str, set[int]] = {}
    for raw in paths.split(b"\0"):
        if not raw or not raw.endswith(b".py"):
            continue
        name = raw.decode("utf-8")
        patch = git(
            root, "diff", "--no-ext-diff", "--no-textconv", "--no-renames", "--unified=0", ancestor, "HEAD", "--", name
        )
        lines: set[int] = set()
        for match in re.finditer(rb"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", patch, re.MULTILINE):
            start, count = int(match[1]), int(match[2]) if match[2] is not None else 1
            lines.update(range(start, start + count))
        result[name] = lines
    return result


def summary(
    report: Report,
    current: dict[str, object],
    baseline: Report | None,
    base: str,
    reason: str,
    url: str,
    changes: dict[str, set[int]] | None,
) -> str:
    """Render separate percentages and bounded missing-line detail without a threshold."""
    output = [
        "## Package coverage — Linux / Python 3.14",
        f"Tested revision: `{current['revision']}`; test outcome: **{current['test_outcome']}**.",
    ]
    if baseline is None:
        output.append(f"Baseline unavailable: {html.escape(reason)}. Current totals remain diagnostic when tests fail.")
    else:
        output.append(f"Baseline: `{base}` ([successful main CI]({url})).")
    table = [
        "| Metric | Baseline covered/total | Baseline | Current covered/total | Current | Change (pp) |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for label, covered, total in (
        ("Lines", "covered_lines", "num_statements"),
        ("Branches", "covered_branches", "num_branches"),
    ):
        counts = report["totals"]
        percent = 100 * counts[covered] / counts[total]
        previous = baseline["totals"] if baseline else None
        before = 100 * previous[covered] / previous[total] if previous else None
        old_counts = f"{previous[covered]}/{previous[total]}" if previous else "—"
        old_percent = f"{before:.2f}%" if before is not None else "—"
        delta = f"{percent - before:+.2f}" if before is not None else "—"
        table.append(
            f"| {label} | {old_counts} | {old_percent} | {counts[covered]}/{counts[total]} | {percent:.2f}% | {delta} |"
        )
    output.append("\n".join(table))
    executed = missing = 0
    details: list[str] = []
    for name, added in sorted((changes or {}).items()):
        safe_name = html.escape(name).replace("`", "&#96;").replace("|", "&#124;")
        measured = report["files"].get(name)
        if measured is None:
            details.append(f"- `{safe_name}`: changed file absent from coverage report.")
            continue
        gaps = sorted(added.intersection(measured["missing_lines"]))
        executed += len(added.intersection(measured["executed_lines"]))
        missing += len(gaps)
        if gaps:
            numbers = ", ".join(map(str, gaps[:50])) + (" …" if len(gaps) > 50 else "")
            details.append(f"- `{safe_name}`: untested changed lines {numbers}.")
    if changes:
        output.append(
            "### Added/modified executable runtime lines\n"
            f"{executed}/{executed + missing} exercised; {missing} untested. "
            "Comments/excluded lines do not count. Renames are treated as new destination files."
        )
        output += details[:20]
        if len(details) > 20:
            output.append(f"Additional files omitted: {len(details) - 20}; inspect the full HTML artifact.")
    elif base and changes is None:
        output.append("Changed-line analysis unavailable: the exact base diff could not be read.")
    elif base:
        output.append("No added/modified runtime Python lines in this diff.")
    output.append(
        "Informational only: no percentage gate. Default pairwise suite; manual/visual/exhaustive tests "
        "and arbitrary CLI subprocesses are excluded. Coverage does not prove useful assertions. "
        "Download `coverage-python-3.14` for JSON, XML, HTML and comparison metadata."
    )
    return "\n\n".join(output) + "\n"


def main() -> int:
    """Publish current metadata and optional comparison without failing for unavailable baselines."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=Path("coverage/coverage.json"))
    parser.add_argument("--base", default="")
    parser.add_argument("--test-outcome", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    report: Report = json.loads(args.report.read_text(encoding="utf-8"))
    validate_report(report)
    current = context(root, report, args.test_outcome)
    args.report.with_name("context.json").write_text(
        json.dumps(current, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    previous = None
    reason, url = "No PR base supplied (main/manual report)", ""
    changes: dict[str, set[int]] | None = None
    if args.base:
        try:
            changes = changed_lines(root, args.base)
            if args.test_outcome == "success":
                previous, url = fetch_baseline(current, args.base)
            else:
                reason = "Current tests failed; no baseline comparison"
        except BaselineUnavailableError as error:
            reason = str(error)
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
            zipfile.BadZipFile,
            subprocess.SubprocessError,
        ):
            reason = "Baseline metadata is malformed or the lookup/diff failed"
    print(summary(report, current, previous, args.base, reason, url, changes), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
