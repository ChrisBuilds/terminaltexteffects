"""Fail incomplete dependency review by comparing GitHub's changes with both universal uv locks."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def normalized_name(name: str) -> str:
    """Use Python package-name normalization for graph/lock comparisons."""
    return re.sub(r"[-_.]+", "-", name).lower()


def lock_pairs(text: str, *, require_registry: bool = True) -> set[tuple[str, str]]:
    """Include every registry version, independent of interpreter/platform markers or group."""
    if sys.version_info >= (3, 11):
        import tomllib as toml  # noqa: PLC0415 - Use the standard parser where available.
    else:
        import tomli as toml  # noqa: PLC0415 - Provided by locked artifact tools on Python 3.9/3.10.

    packages = toml.loads(text)["package"]
    pairs: set[tuple[str, str]] = set()
    for package in packages:
        source = package["source"]
        if "registry" in source:
            pairs.add((normalized_name(package["name"]), package["version"]))
        elif source not in ({"editable": "."}, {"virtual": "."}) and require_registry:
            message = f"Cannot verify non-registry dependency {package['name']}; review and extend the gate explicitly."
            raise ValueError(message)
    return pairs


def missing_changes(base: set[tuple[str, str]], head: set[tuple[str, str]], changes: object) -> list[str]:
    """Require every added/removed registry pair in GitHub's uv.lock comparison."""
    if not isinstance(changes, list):
        message = "Dependency review output must be a JSON array; missing output is not a pass."
        raise TypeError(message)
    reported: dict[str, set[tuple[str, str]]] = {"added": set(), "removed": set()}
    for entry in changes:
        if not isinstance(entry, dict):
            message = "Invalid dependency change entry"
            raise TypeError(message)
        if entry.get("manifest") != "uv.lock" or entry.get("ecosystem") != "pip":
            continue
        kind = entry["change_type"]
        name, version = entry["name"], entry["version"]
        if kind not in reported or not isinstance(name, str) or not isinstance(version, str):
            message = "Invalid uv.lock change type, package name, or version"
            raise ValueError(message)
        reported[kind].add((normalized_name(name), version))
    problems = []
    for kind, expected in (("added", head - base), ("removed", base - head)):
        problems.extend(
            f"Missing {kind} uv.lock pair: {name}=={version}" for name, version in sorted(expected - reported[kind])
        )
    return problems


def revision_lock(root: Path, revision: str) -> str:
    """Read a committed lock without checking out or executing PR content."""
    return subprocess.run(  # noqa: S603 - Revision passed as a Git argument, never shell text.
        ["git", "show", f"{revision}:uv.lock"],  # noqa: S607 - Use the environment's Git binary.
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def main() -> int:
    """Validate the official action's JSON output without downloading packages or changing the lock."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        base = lock_pairs(revision_lock(root, args.base), require_registry=False)
        head = lock_pairs(revision_lock(root, args.head))
        changes = json.loads(os.environ["DEPENDENCY_CHANGES"])
        problems = missing_changes(base, head, changes)
    except (KeyError, ValueError, TypeError, OSError, subprocess.CalledProcessError) as error:
        print(f"Dependency review coverage failed: {error}", file=sys.stderr)
        return 1
    if problems:
        print("Dependency review coverage failed:\n" + "\n".join(problems), file=sys.stderr)
        return 1
    print(f"Dependency review covers {len(head - base)} added and {len(base - head)} removed registry pairs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
