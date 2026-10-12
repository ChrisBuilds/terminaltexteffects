"""Validate Towncrier changelog fragments and render the Unreleased preview."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_START = "<!-- towncrier release notes start -->"
EMPTY_PREVIEW = "## Unreleased\n\nNo pending user-facing changes."
FRAGMENT_NAME = re.compile(
    r"(?:[1-9]\d*|\+[a-z0-9][a-z0-9-]*)\.(?:breaking|added|changed|deprecated|removed|fixed|security)(?:\.\d+)?\.md",
)
IGNORED_FILES = {"README.md", "template.md.jinja"}
RELEASE_HEADER = re.compile(r"^## \S+ - [0-9]{4}-[0-9]{2}-[0-9]{2}$", re.MULTILINE)


def git_output(root: Path, *args: str) -> bytes:
    """Read Git state with argument separation and no shell."""
    return subprocess.run(  # noqa: S603 - Git arguments are passed without a shell.
        ["git", *args],  # noqa: S607 - Use the environment's Git installation.
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout


def changed_fragments(root: Path, ancestor: str, diff_filter: str) -> list[str]:
    """List fragment names changed since `ancestor` with the given Git diff filter."""
    output = git_output(root, "diff", "--name-only", f"--diff-filter={diff_filter}", "-z", ancestor, "HEAD")
    names = [Path(name.decode()).name for name in output.split(b"\0") if name.startswith(b"changelog.d/")]
    return [name for name in names if FRAGMENT_NAME.fullmatch(name)]


def validate_decision(root: Path, base: str) -> None:
    """Require an added fragment, or fragments consumed into a new dated release section."""
    ancestor = git_output(root, "merge-base", base, "HEAD").decode().strip()
    if changed_fragments(root, ancestor, "AMR"):
        return
    if changed_fragments(root, ancestor, "D"):
        before = git_output(root, "show", f"{ancestor}:CHANGELOG.md").decode()
        after = (root / "CHANGELOG.md").read_text(encoding="utf-8")
        if set(RELEASE_HEADER.findall(after)) - set(RELEASE_HEADER.findall(before)):
            return
    message = (
        "No changelog fragment added. Add changelog.d/<issue-or-PR>.<category>.md for user-facing changes, "
        "or apply the no-changelog label to the PR."
    )
    raise ValueError(message)


def validate_fragments(directory: Path) -> None:
    """Reject invalid names and empty notes before rendering."""
    for path in sorted(directory.iterdir()):
        if path.name in IGNORED_FILES:
            continue
        if not path.is_file() or FRAGMENT_NAME.fullmatch(path.name) is None:
            message = f"Invalid changelog fragment: {path.name}"
            raise ValueError(message)
        if not path.read_text(encoding="utf-8").strip():
            message = f"Empty changelog fragment: {path.name}"
            raise ValueError(message)


def render_preview(root: Path = ROOT) -> str:
    """Render pending fragments as an Unreleased section without consuming them."""
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


def insert_preview(changelog: str, preview: str) -> str:
    """Insert the preview above published history."""
    if changelog.count(RELEASE_START) != 1:
        message = f"The changelog must contain exactly one {RELEASE_START} marker."
        raise ValueError(message)
    return changelog.replace(RELEASE_START, f"{RELEASE_START}\n\n{preview.strip()}\n", 1)


def release_notes(changelog: str, version: str) -> str:
    """Return the body of the dated `## <version> - <date>` section, without its heading."""
    heading = re.search(rf"^## {re.escape(version)} - [0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$", changelog, re.MULTILINE)
    if heading is None:
        message = f"CHANGELOG.md has no dated section for {version}."
        raise ValueError(message)
    body = changelog[heading.end() :]
    following = re.search(r"^## ", body, re.MULTILINE)
    return (body[: following.start()] if following else body).strip()


def main() -> int:
    """Validate fragments, optionally require a changelog decision, or print the preview."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="Require an added fragment in committed changes since this Git base.")
    parser.add_argument("--preview", action="store_true", help="Print the rendered Unreleased section.")
    parser.add_argument("--release-notes", metavar="VERSION", help="Print the dated section for VERSION.")
    args = parser.parse_args()
    if args.release_notes:
        try:
            print(release_notes((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), args.release_notes))
        except ValueError as error:
            print(error, file=sys.stderr)
            return 1
        return 0
    try:
        validate_fragments(ROOT / "changelog.d")
        if args.base:
            validate_decision(ROOT, args.base)
        preview = render_preview(ROOT)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    if args.preview:
        print(preview)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
