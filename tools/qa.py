"""Preview or run focused local QA against branch and working-tree changes."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from tools.check_workflows import workflow_files
from tools.classify_ci import needs_documentation_build
from tools.run_hook import check_hygiene


def git(root: Path, *args: str) -> bytes:
    """Read Git state without a shell or changes to the index."""
    return subprocess.run(  # noqa: S603 - Separate Git arguments, no shell.
        ["git", *args],  # noqa: S607 - Use the environment Git executable.
        cwd=root,
        capture_output=True,
        check=True,
    ).stdout


def changed_files(root: Path, base: str) -> list[str]:
    """Include committed, staged, unstaged and untracked changes, retaining deletions."""
    ancestor = git(root, "merge-base", base, "HEAD").decode().strip()
    outputs = (
        git(root, "diff", "--name-only", "--no-renames", "-z", ancestor, "HEAD", "--"),
        git(root, "diff", "--cached", "--name-only", "--no-renames", "-z", "HEAD", "--"),
        git(root, "diff", "--name-only", "--no-renames", "-z", "--"),
        git(root, "ls-files", "--others", "--exclude-standard", "-z"),
    )
    return sorted({os.fsdecode(name) for output in outputs for name in output.split(b"\0") if name})


def plan(root: Path, names: list[str], tests: list[str], keyword: str | None) -> list[tuple[str, list[str]]]:
    """Build read-only checks; never infer a broad pytest selection."""
    commands: list[tuple[str, list[str]]] = []
    python = sys.executable
    files = [f"./{name}" for name in names if (root / name).is_file() and not (root / name).is_symlink()]
    pyfiles = [name for name in files if name.endswith((".py", ".pyi"))]
    if tests:
        command = [python, "-m", "pytest", *[f"./{node}" for node in tests]]
        if keyword:
            command.extend(["-k", keyword])
        commands.append(("Explicit focused tests", command))
    if pyfiles:
        commands.extend(
            [
                ("Python formatting (read-only)", [python, "-m", "ruff", "format", "--check", *pyfiles]),
                ("Python lint (read-only)", [python, "-m", "ruff", "check", *pyfiles]),
                ("Python types", [python, "-m", "pyright", "--pythonpath", python, *pyfiles]),
            ]
        )
    if names:
        commands.append(("Changelog fragments and preview", [python, "tools/generate_changelog.py", "--check"]))
    if any(name.startswith(".github/workflows/") or name == "tools/check_workflows.py" for name in names):
        workflow_paths = set(workflow_files(root))
        workflow_paths.update(
            name
            for name in names
            if name.startswith(".github/workflows/") and name.endswith((".yml", ".yaml")) and (root / name).is_file()
        )
        commands.append(
            (
                "Tracked and changed untracked workflows (actionlint/ShellCheck required)",
                [python, "tools/check_workflows.py", *sorted(workflow_paths)],
            )
        )
    if any(
        name.startswith("terminaltexteffects/")
        or name in {"tools/generate_shell_completions.py", "tools/completions/powershell.ps1"}
        for name in names
    ):
        commands.append(("Generated shell completions", [python, "tools/generate_shell_completions.py", "--check"]))
    if any(
        name.startswith(("terminaltexteffects/", "docs/effects/", "tests/effects_tests/"))
        or name in {"mkdocs.yml", "tools/check_effect_inventory.py"}
        for name in names
    ):
        commands.append(("Shipped effect inventory", [python, "tools/check_effect_inventory.py"]))
    if any(needs_documentation_build(name) for name in names):
        commands.append(("Strict documentation build", [python, "-m", "mkdocs", "build", "--strict"]))
    return commands


def main(argv: list[str] | None = None) -> int:
    """Explain checks and return the first failure, without fixes, installation or retries."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main", help="Local Git comparison ref; no automatic fetch.")
    parser.add_argument(
        "--test", action="append", default=[], help="Existing test file or node; repeat for multiple selections."
    )
    parser.add_argument("-k", dest="keyword", help="Filter the explicitly selected tests.")
    parser.add_argument("--dry-run", action="store_true", help="Explain the plan without executing checks.")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    if args.keyword and not args.test:
        parser.error("-k requires --test")
    for node in args.test:
        path = Path(node.split("::", 1)[0])
        if (
            path.is_absolute()
            or ".." in path.parts
            or not path.parts
            or path.parts[0] != "tests"
            or path.suffix != ".py"
            or not (root / path).is_file()
        ):
            parser.error("--test must be an existing repository-relative tests/*.py file or node")
    try:
        names = changed_files(root, args.base)
    except subprocess.CalledProcessError as error:
        print(error.stderr.decode(errors="replace"), file=sys.stderr)
        return error.returncode
    files = [str(root / name) for name in names]
    commands = plan(root, names, args.test, args.keyword)
    print(
        f"Base: {args.base}; checks use current working-tree contents, including staged/untracked changes.", flush=True
    )
    print(f"Changed paths: {names!r}", flush=True)
    print("Text hygiene: existing changed files", flush=True)
    for reason, command in commands:
        print(f"{reason}: {command!r}", flush=True)
    if not args.test:
        print("Tests NOT RUN: select focused nodes with --test; broad suites remain in CI.", flush=True)
    print("CI still validates all tracked Python, dependencies, artifacts and the platform matrix.", flush=True)
    if args.dry_run:
        return 0
    if check_hygiene(files):
        return 1
    for reason, command in commands:
        print(f"Running: {reason}", flush=True)
        result = subprocess.run(command, cwd=root, check=False)  # noqa: S603 - Argument arrays, no shell.
        if result.returncode:
            return result.returncode
    print("Selected local checks passed; this is not a complete CI result.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
