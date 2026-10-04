"""Refresh the Unreleased changelog preview from validated Towncrier fragments."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

PREVIEW_START = "<!-- unreleased notes start -->"
PREVIEW_END = "<!-- unreleased notes end -->"
RELEASE_START = "<!-- towncrier release notes start -->"
EMPTY_PREVIEW = "## Unreleased\n\nNo pending user-facing changes."
FRAGMENT_NAME = re.compile(
    r"(?:[1-9]\d*|\+[a-z0-9][a-z0-9-]*)\."
    r"(?:breaking|added|changed|deprecated|removed|fixed|security|skip)(?:\.\d+)?\.md",
)
IGNORED_FILES = {"README.md", "template.md.jinja"}


def git_output(root: Path, *args: str) -> bytes:
    """Read Git state with argument separation and no shell."""
    return subprocess.run(  # noqa: S603 - Git arguments are passed without a shell.
        ["git", *args],  # noqa: S607 - Use the environment's Git installation.
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout


def validate_decision(root: Path, base: str) -> None:
    """Require a changed fragment, or fragment consumption into a new dated release."""
    ancestor = git_output(root, "merge-base", base, "HEAD").decode().strip()
    changed = git_output(root, "diff", "--name-only", "--diff-filter=AMR", "-z", ancestor, "HEAD", "--", "changelog.d")
    if any(FRAGMENT_NAME.fullmatch(Path(name.decode()).name) for name in changed.split(b"\0") if name):
        return
    deleted = git_output(root, "diff", "--name-only", "--diff-filter=D", "-z", ancestor, "HEAD", "--", "changelog.d")
    if any(FRAGMENT_NAME.fullmatch(Path(name.decode()).name) for name in deleted.split(b"\0") if name):
        before = git_output(root, "show", f"{ancestor}:CHANGELOG.md").decode()
        after = (root / "CHANGELOG.md").read_text(encoding="utf-8")
        release_pattern = r"^## \S+ - [0-9]{4}-[0-9]{2}-[0-9]{2}$"
        previous_headers = set(re.findall(release_pattern, before.partition(RELEASE_START)[2], re.MULTILINE))
        current_headers = set(re.findall(release_pattern, after.partition(RELEASE_START)[2], re.MULTILINE))
        if current_headers - previous_headers:
            return
    message = (
        "Add an issue-numbered changelog note or .skip.md reason; preview edits alone are not a changelog decision."
    )
    raise ValueError(message)


def validate_fragments(directory: Path) -> None:
    """Reject invalid names and empty notes or skip reasons before rendering."""
    for path in sorted(directory.iterdir()):
        if path.name in IGNORED_FILES:
            continue
        if not path.is_file() or FRAGMENT_NAME.fullmatch(path.name) is None:
            message = f"Invalid changelog fragment: {path.name}"
            raise ValueError(message)
        if not path.read_text(encoding="utf-8").strip():
            message = f"Empty changelog fragment or skip reason: {path.name}"
            raise ValueError(message)


def render_preview(root: Path) -> str:
    """Render notes without modifying the changelog or consuming fragments."""
    result = subprocess.run(
        [sys.executable, "-m", "towncrier", "build", "--draft", "--version", "Unreleased", "--date", "1970-01-01"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        sys.stderr.write(result.stderr)
    result.check_returncode()
    return result.stdout.strip()


def replace_preview(changelog: str, preview: str) -> str:
    """Replace only the marked preview, preserving all published release text."""
    if changelog.count(PREVIEW_START) != 1 or changelog.count(PREVIEW_END) != 1:
        message = "The changelog must have exactly one pair of Unreleased preview markers."
        raise ValueError(message)
    prefix, _, remainder = changelog.partition(PREVIEW_START)
    _, separator, suffix = remainder.partition(PREVIEW_END)
    if not separator:
        message = "The Unreleased preview end marker must follow its start marker."
        raise ValueError(message)
    return f"{prefix}{PREVIEW_START}\n\n{preview.strip()}\n\n{PREVIEW_END}{suffix}"


def main() -> int:
    """Generate or check the preview, or clear it before assembling a release."""
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check", action="store_true", help="Fail if fragments or the preview are invalid; write nothing."
    )
    mode.add_argument(
        "--clear", action="store_true", help="Clear the preview before Towncrier assembles a dated release."
    )
    parser.add_argument("--base", help="Require a changelog decision in committed changes since this Git base.")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    validate_fragments(root / "changelog.d")
    if args.base:
        validate_decision(root, args.base)
    path = root / "CHANGELOG.md"
    original = path.read_text(encoding="utf-8")
    updated = replace_preview(original, EMPTY_PREVIEW if args.clear else render_preview(root))
    if args.check:
        if updated != original:
            print("Changelog preview is stale; run ./.venv/bin/python tools/generate_changelog.py.")
            return 1
        print("Changelog fragments and Unreleased preview are current.")
    else:
        path.write_text(updated, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
