"""Record a small, explicit set of CI reproduction details without environment dumps."""

from __future__ import annotations

import argparse
import json
import os
import platform
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def context() -> dict[str, object]:
    """Return interpreter, tool versions, and whitelisted workflow revision identifiers."""
    packages: dict[str, str | None] = {}
    for name in ("pytest", "pytest-xdist", "pytest-cov", "coverage"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:  # noqa: PERF203 - Four metadata lookups, not a test hot path.
            packages[name] = None
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.system(),
        "packages": packages,
        "revision": os.environ.get("GITHUB_SHA"),
        "pr_head": os.environ.get("DIAGNOSTICS_HEAD"),
        "base": os.environ.get("DIAGNOSTICS_BASE"),
        "repository": os.environ.get("GITHUB_REPOSITORY"),
        "event": os.environ.get("GITHUB_EVENT_NAME"),
        "job": os.environ.get("GITHUB_JOB"),
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "cpu_count": os.cpu_count(),
    }


def main() -> None:
    """Write metadata beside JUnit reports; pytest commands remain in the workflow."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("test-results/context.json"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(context(), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
