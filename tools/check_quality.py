"""Check formatting, lint, and types for Python files changed since a Git base."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def changed_python_files(root: Path, base: str, head: str) -> list[str]:
    """Select existing Python files from the merge-base diff, including rename destinations."""
    ancestor = subprocess.run(  # noqa: S603 - Git arguments are passed without a shell.
        ["git", "merge-base", base, head],  # noqa: S607 - Use the runner's Git installation.
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    result = subprocess.run(  # noqa: S603 - Revisions and paths are separate arguments.
        ["git", "diff", "--name-only", "--diff-filter=ACMR", "-z", ancestor, head, "--"],  # noqa: S607
        cwd=root,
        check=True,
        capture_output=True,
    )
    return [
        f"./{name}"
        for raw_name in result.stdout.split(b"\0")
        if raw_name
        for name in [raw_name.decode("utf-8")]
        if name.endswith((".py", ".pyi")) and (root / name).is_file()
    ]


def main() -> int:
    """Run read-only checks, returning the first failing tool's status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="Git revision to compare against.")
    parser.add_argument("--head", default="HEAD", help="Git revision being checked.")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    files = changed_python_files(root, args.base, args.head)
    if not files:
        print("No changed Python files; quality checks passed.")
        return 0
    commands = (
        [sys.executable, "-m", "ruff", "format", "--check", *files],
        [sys.executable, "-m", "ruff", "check", *files],
        [sys.executable, "-m", "pyright", "--pythonpath", sys.executable, *files],
    )
    for command in commands:
        result = subprocess.run(command, cwd=root, check=False)  # noqa: S603 - No shell or automatic fixes.
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
