"""Run staged-file QA using the same project environment and settings as CI."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def changelog_path(name: str) -> bool:
    """Identify inputs to changelog validation, including fragment deletions."""
    return name.startswith("changelog.d/") or name in {
        "CHANGELOG.md",
        "tools/generate_changelog.py",
        "pyproject.toml",
        "uv.lock",
    }


def staged_changelog_changes(root: Path) -> bool:
    """Check both sides of staged renames without reading unstaged changes."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--no-renames", "--name-only", "-z", "--"],  # noqa: S607
        cwd=root,
        check=True,
        capture_output=True,
    )
    return any(changelog_path(name.decode("utf-8")) for name in result.stdout.split(b"\0") if name)


def main(argv: list[str] | None = None) -> int:
    """Run one hook and propagate failures; never expand an empty list to the whole project."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("check", choices=("lint", "format", "types", "changelog"))
    parser.add_argument("files", nargs="*")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    if args.check == "changelog":
        if not any(changelog_path(name) for name in args.files) and not staged_changelog_changes(root):
            return 0
        # The staged snapshot is supplied by pre-commit. Do not use --base, which
        # validates committed revisions and cannot see this pending commit.
        command = [sys.executable, str(root / "tools/generate_changelog.py"), "--check"]
    else:
        if not args.files:
            return 0
        # Relative prefixes keep unusual filenames from becoming tool options.
        files = [f"./{name}" for name in args.files]
        commands = {
            "lint": [sys.executable, "-m", "ruff", "check", "--fix", "--no-unsafe-fixes", *files],
            "format": [sys.executable, "-m", "ruff", "format", *files],
            "types": [sys.executable, "-m", "pyright", "--pythonpath", sys.executable, *files],
        }
        command = commands[args.check]
    return subprocess.run(command, cwd=root, check=False).returncode  # noqa: S603 - No shell.


if __name__ == "__main__":
    raise SystemExit(main())
