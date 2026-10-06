"""Validate tracked GitHub Actions workflows with pinned actionlint and required ShellCheck."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ACTIONLINT_VERSION = "1.7.12"


def workflow_files(root: Path) -> list[str]:
    """Select existing tracked workflows, including both supported YAML extensions."""
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", ".github/workflows"],  # noqa: S607 - Use installed Git.
        cwd=root,
        capture_output=True,
        check=True,
    )
    return sorted(
        name
        for raw in result.stdout.split(b"\0")
        if raw
        for name in [raw.decode("utf-8")]
        if name.endswith((".yml", ".yaml")) and (root / name).is_file()
    )


def executable(variable: str, default: str) -> str:
    """Resolve an explicit tool override or PATH installation, failing if unavailable."""
    selected = os.environ.get(variable, default)
    path = shutil.which(selected)
    if path is None:
        message = f"Missing {default}: install it or set {variable} to its executable path."
        raise RuntimeError(message)
    return path


def check(files: list[str], root: Path) -> int:
    """Run read-only lint with explicit integrations; propagate errors without downloading or editing files."""
    if not files:
        print("No selected workflows; workflow lint passed.")
        return 0
    try:
        actionlint = executable("TTE_ACTIONLINT", "actionlint")
        shellcheck = executable("TTE_SHELLCHECK", "shellcheck")
        version = subprocess.run(  # noqa: S603 - Resolved executable, no shell.
            [actionlint, "-version"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        if not version or version[0] != ACTIONLINT_VERSION:
            print(
                f"Workflow lint failed: install actionlint {ACTIONLINT_VERSION}; found {version[:1]}.", file=sys.stderr
            )
            return 1
        # Pyflakes is disabled explicitly; the result must not depend on its presence on PATH.
        return subprocess.run(  # noqa: S603 - Absolute filenames prevent option injection.
            [actionlint, "-shellcheck", shellcheck, "-pyflakes", "", *(str((root / name).resolve()) for name in files)],
            cwd=root,
            check=False,
        ).returncode
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print(f"Workflow lint failed: {error}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    """Check explicit hook paths or all tracked workflows when invoked without paths."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", help="Workflow paths; defaults to all tracked workflows.")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    return check(args.files or workflow_files(root), root)


if __name__ == "__main__":
    raise SystemExit(main())
