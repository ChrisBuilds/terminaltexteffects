"""Select CI work conservatively from committed changes; unknown paths require tests."""

from __future__ import annotations

import argparse
from pathlib import Path

from tools.generate_changelog import git_output

DOCUMENTATION_SUFFIXES = {".md", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}


def is_documentation(name: str) -> bool:
    """Recognize prose and documentation images without exempting scripts or configuration."""
    path = Path(name)
    if len(path.parts) == 1:
        return path.suffix == ".md"
    if path.parts[0] == "docs":
        return path.suffix in DOCUMENTATION_SUFFIXES
    if path.parts[0] == "changelog.d":
        return path.suffix == ".md"
    return path.parts[0] == ".github" and path.suffix == ".md" and "workflows" not in path.parts


def classify_changes(root: Path, base: str | None, head: str = "HEAD") -> tuple[bool, bool]:
    """Return test and documentation requirements, including deletions and both rename paths."""
    if not base or set(base) == {"0"}:
        return True, True
    ancestor = git_output(root, "merge-base", base, head).decode().strip()
    changed = git_output(root, "diff", "--name-only", "--no-renames", "-z", ancestor, head, "--")
    names = [name.decode() for name in changed.split(b"\0") if name]
    run_tests = any(not is_documentation(name) for name in names)
    build_docs = any(is_documentation(name) or name == "mkdocs.yml" or name.startswith("overrides/") for name in names)
    return run_tests, build_docs


def main() -> int:
    """Emit GitHub step outputs; omitting a base requests complete manual validation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="Git comparison base; omit for a full manual run.")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    run_tests, build_docs = classify_changes(root, args.base)
    print(f"run_tests={str(run_tests).lower()}")
    print(f"build_docs={str(build_docs).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
