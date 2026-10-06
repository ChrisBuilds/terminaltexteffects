"""Verify staged-file QA dispatch and real pre-commit behavior."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import sysconfig
from importlib.util import find_spec
from pathlib import Path
from typing import Literal

import pytest

from tools import generate_changelog, run_hook


@pytest.fixture(autouse=True)
def isolated_uv_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep disposable hook environments and uv metadata away from personal caches."""
    monkeypatch.setenv("UV_CACHE_DIR", str(tmp_path / "uv-cache"))


@pytest.fixture(autouse=True)
def require_integration_tools() -> None:
    """Fail required CI integration instead of silently skipping missing QA tools."""
    if os.environ.get("TTE_REQUIRE_HOOK_INTEGRATION") == "1":
        missing = [module for module in ("pre_commit", "ruff", "pyright") if find_spec(module) is None]
        assert not missing, f"Required hook tools missing: {missing}"
        assert shutil.which("uv") is not None, "Required hook integration needs uv on PATH"


def prepare_hook_environment(root: Path) -> None:
    """Create a native venv without symlink privileges or reinstalling locked test tools."""
    uv = shutil.which("uv")
    if uv is None:
        pytest.fail("Real hook integration requires uv on PATH")
    result = subprocess.run(  # noqa: S603 - Explicit local venv creation without a shell.
        [uv, "venv", "--offline", "--python", sys.executable, str(root / ".venv")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    python = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    site = subprocess.run(  # noqa: S603 - Query only the disposable environment.
        [str(python), "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    Path(site, "locked-test-tools.pth").write_text(sysconfig.get_path("purelib") + "\n", encoding="utf-8")


@pytest.mark.parametrize(
    ("name", "data", "expected"),
    [
        ("with spaces.txt", b"valid\r\n", 0),
        ("notes.txt", b"invalid \n", 1),
        ("notes.txt", b"invalid\t\r\n", 1),
        ("notes.md", b"hard break  \r\n", 0),
        ("notes.md", b"single space \n", 1),
        ("notes.md", b" \t\n", 1),
        ("notes.md", b"hard break\t \n", 1),
        ("notes.txt", b"<<<<<<< HEAD\n", 1),
        ("notes.txt", b">>>>>>> branch\n", 1),
        ("notes.txt", b"||||||| base\n", 1),
        ("notes.txt", b"=======\n", 1),
        ("notes.txt", b"======== ordinary text\n", 0),
        ("data.bin", b"\0<<<<<<< HEAD\ninvalid \n", 0),
    ],
)
def test_hygiene_is_read_only_and_preserves_markdown_breaks(
    tmp_path: Path,
    name: str,
    data: bytes,
    expected: int,
) -> None:
    """Validate text hygiene with CRLF, Markdown, paths with spaces, and binary inputs."""
    selected = tmp_path / name
    selected.write_bytes(data)
    assert run_hook.main(["hygiene", "--", str(selected)]) == expected
    assert selected.read_bytes() == data


def test_hygiene_checks_only_selected_existing_files(tmp_path: Path) -> None:
    """Unselected files and deletions cannot expand a hook into a whole checkout scan."""
    (tmp_path / "unselected.txt").write_text("invalid \n", encoding="utf-8")
    assert run_hook.main(["hygiene"]) == 0
    assert run_hook.main(["hygiene", str(tmp_path / "deleted.txt")]) == 0


@pytest.mark.parametrize("check", ["lint", "format", "types"])
def test_hook_empty_file_list_does_not_check_entire_project(check: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """No selected Python files means no invocation of project-wide checks."""

    def unexpected(*_args: object, **_kwargs: object) -> None:
        pytest.fail("Empty file selection must not run a tool.")

    monkeypatch.setattr(run_hook.subprocess, "run", unexpected)
    assert run_hook.main([check]) == 0


@pytest.mark.parametrize("check", ["lint", "format", "types"])
def test_hook_uses_current_environment_preserves_paths_and_propagates_failure(
    check: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Arguments remain separate, safe fixes are explicit, and failures block commits."""
    commands: list[list[str]] = []

    def capture(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        assert kwargs["check"] is False
        return subprocess.CompletedProcess(command, 7)

    monkeypatch.setattr(run_hook.subprocess, "run", capture)
    assert run_hook.main([check, "--", "file with spaces.py", "--version.pyi"]) == 7
    command = commands[0]
    assert command[0] == sys.executable
    assert command[-2:] == ["./file with spaces.py", "./--version.pyi"]
    if check == "lint":
        assert "--fix" in command
        assert "--no-unsafe-fixes" in command
    if check == "types":
        assert command[command.index("--pythonpath") + 1] == sys.executable


@pytest.mark.parametrize("changed", [b"changelog.d/1.fixed.md\0", b"CHANGELOG.md\0", b"tools/example.py\0"])
def test_changelog_hook_detects_deleted_and_renamed_staged_inputs(
    changed: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing fragment can still trigger validation through the staged Git diff."""
    commands: list[list[str]] = []
    validated: list[Path] = []
    monkeypatch.setattr(run_hook, "validate_staged_changelog", lambda root: validated.append(root) or 0)

    def capture(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=changed)

    monkeypatch.setattr(run_hook.subprocess, "run", capture)
    assert run_hook.main(["changelog"]) == 0
    assert "--cached" in commands[0]
    assert "--no-renames" in commands[0]
    assert len(commands) == 1
    assert bool(validated) is not changed.startswith(b"tools/example.py")


@pytest.mark.skipif(
    any(find_spec(module) is None for module in ("pre_commit", "ruff", "pyright")),
    reason="Real hook integration runs in Code quality with locked development tools.",
)
@pytest.mark.parametrize("layout", ["separate", "overlapping"])
def test_pre_commit_fixes_require_restaging_and_preserve_unstaged_changes(
    tmp_path: Path,
    layout: Literal["separate", "overlapping"],
) -> None:
    """Exercise real staging isolation, a formatter fix, and a failing Pyright check."""
    root = Path(__file__).resolve().parents[1]
    environment = {**os.environ, "PRE_COMMIT_HOME": str(tmp_path / "cache")}

    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603 - Test commands have separated arguments.
            list(args),
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def git(*args: str) -> str:
        result = run("git", *args)
        assert result.returncode == 0, result.stderr
        return result.stdout

    git("init")
    (tmp_path / "tools").mkdir()
    shutil.copy(root / "tools/run_hook.py", tmp_path / "tools/run_hook.py")
    shutil.copy(root / ".pre-commit-config.yaml", tmp_path / ".pre-commit-config.yaml")
    prepare_hook_environment(tmp_path)
    # Isolate staging/formatting semantics from changes to Ruff's default rule selection.
    (tmp_path / "pyproject.toml").write_text(
        '[tool.ruff.lint]\nselect = ["F"]\n\n[tool.pyright]\npythonVersion = "3.9"\n',
        encoding="utf-8",
    )
    source = tmp_path / "example.py"
    tail = "" if layout == "overlapping" else "".join(f"value_{index}: int = {index}\n" for index in range(6))
    staged = "value: int=1\n" + tail
    unstaged = staged + "# Keep this unstaged comment.\n"
    source.write_text(staged, encoding="utf-8")
    git("add", "example.py", "tools/run_hook.py", ".pre-commit-config.yaml")
    source.write_text(unstaged, encoding="utf-8")
    result = run(sys.executable, "-m", "pre_commit", "run")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "files were modified by this hook" in result.stdout
    expected = unstaged if layout == "overlapping" else "value: int = 1\n" + tail + "# Keep this unstaged comment.\n"
    assert source.read_text(encoding="utf-8") == expected
    assert git("show", ":example.py") == staged
    assert run(sys.executable, "-m", "ruff", "format", "example.py", "tools/run_hook.py").returncode == 0
    git("add", "example.py", "tools/run_hook.py")
    result = run(sys.executable, "-m", "pre_commit", "run")
    assert result.returncode == 0, result.stdout + result.stderr
    source.write_text('value: int = "wrong type"\n', encoding="utf-8")
    git("add", "example.py")
    result = run(sys.executable, "-m", "pre_commit", "run", "pyright")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "reportAssignmentType" in result.stdout


@pytest.fixture
def changelog_repository(tmp_path: Path) -> Path:
    """Create a real indexed changelog with the project's renderer and configuration."""
    root = Path(__file__).resolve().parents[1]
    (tmp_path / "tools").mkdir()
    for name in ("tools/run_hook.py", "tools/generate_changelog.py", "pyproject.toml"):
        shutil.copy(root / name, tmp_path / name)
    fragments = tmp_path / "changelog.d"
    fragments.mkdir()
    shutil.copy(root / "changelog.d/template.md.jinja", fragments / "template.md.jinja")
    (fragments / "123.fixed.md").write_text("Baseline release note.\n", encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(
        f"# Changelog\n{generate_changelog.PREVIEW_START}\n{generate_changelog.PREVIEW_END}\n"
        f"{generate_changelog.RELEASE_START}\n## 0.15.0\nPublished history.\n",
        encoding="utf-8",
    )
    assert changelog_command(tmp_path, "generate_changelog.py").returncode == 0
    git_changelog(tmp_path, "init")
    git_changelog(tmp_path, "add", ".")
    git_changelog(
        tmp_path,
        "-c",
        "user.name=Hook Test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "--no-verify",
        "-m",
        "Baseline",
    )
    (fragments / "124.skip.md").write_text("Internal tooling.\n", encoding="utf-8")
    git_changelog(tmp_path, "add", "changelog.d/124.skip.md")
    return tmp_path


def changelog_command(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run a real renderer or hook against the disposable repository."""
    return subprocess.run(  # noqa: S603 - Separated arguments; no shell.
        [sys.executable, str(root / "tools" / arguments[0]), *arguments[1:]],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )


def test_changelog_hook_ignores_untracked_invalid_fragments(changelog_repository: Path) -> None:
    """An untracked invalid note cannot block a valid indexed changelog."""
    fragment = changelog_repository / "changelog.d" / "not-a-fragment.txt"
    fragment.write_text("Unrelated draft", encoding="utf-8")
    result = changelog_command(changelog_repository, "run_hook.py", "changelog")
    assert result.returncode == 0, result.stdout + result.stderr
    assert fragment.read_text(encoding="utf-8") == "Unrelated draft"


def git_changelog(root: Path, *arguments: str) -> str:
    """Inspect and update only the disposable repository's index."""
    return subprocess.run(  # noqa: S603 - Separated Git arguments without a shell.
        ["git", *arguments],  # noqa: S607 - Use the environment's Git binary.
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    ).stdout


def test_ci_hygiene_selects_additions_and_rename_destinations(changelog_repository: Path) -> None:
    """Committed selection includes spaces/renames, excludes deletions and untracked drafts."""
    root = changelog_repository
    git_changelog(root, "mv", "changelog.d/123.fixed.md", "renamed file.md")
    git_changelog(root, "rm", "CHANGELOG.md")
    (root / "new.txt").write_text("invalid \n", encoding="utf-8")
    (root / "draft.txt").write_text("untracked \n", encoding="utf-8")
    git_changelog(root, "add", "new.txt")
    git_changelog(
        root, "-c", "user.name=Hook Test", "-c", "user.email=test@example.com", "commit", "--no-verify", "-m", "Change"
    )
    names = {Path(name).relative_to(root).as_posix() for name in run_hook.changed_hygiene_files(root, "HEAD^")}
    assert names == {"new.txt", "renamed file.md", "changelog.d/124.skip.md"}
    assert run_hook.check_hygiene(run_hook.changed_hygiene_files(root, "HEAD^")) == 1
    assert run_hook.changed_hygiene_files(root, "HEAD") == []


@pytest.mark.skipif(find_spec("pre_commit") is None, reason="Real hook integration requires locked tools.")
@pytest.mark.parametrize("staged_bad", [False, True])
def test_pre_commit_hygiene_validates_index_preserving_worktree(
    changelog_repository: Path, *, staged_bad: bool
) -> None:
    """Neither clean unstaged text nor bad unstaged text can change the index-only result."""
    root = Path(__file__).resolve().parents[1]
    repository = changelog_repository
    shutil.copy(root / ".pre-commit-config.yaml", repository / ".pre-commit-config.yaml")
    prepare_hook_environment(repository)
    selected = repository / "notes with spaces.txt"
    staged = "bad \n" if staged_bad else "good\n"
    unstaged = "good\n" if staged_bad else "<<<<<<< HEAD\n"
    selected.write_text(staged, encoding="utf-8")
    git_changelog(repository, "add", ".pre-commit-config.yaml", selected.name)
    selected.write_text(unstaged, encoding="utf-8")
    before = git_changelog(repository, "diff", "--cached")
    result = subprocess.run(
        [sys.executable, "-m", "pre_commit", "run", "hygiene"],
        cwd=repository,
        env={**os.environ, "PRE_COMMIT_HOME": str(repository / "cache")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == int(staged_bad), result.stdout + result.stderr
    assert selected.read_text(encoding="utf-8") == unstaged
    assert git_changelog(repository, "diff", "--cached") == before
    assert not (repository / "uv.lock").exists()


def test_changelog_hook_rejects_preview_including_untracked_note(changelog_repository: Path) -> None:
    """A staged preview cannot pass by referring to a fragment absent from the index."""
    fragment = changelog_repository / "changelog.d/125.fixed.md"
    fragment.write_text("Uncommitted change.\n", encoding="utf-8")
    assert changelog_command(changelog_repository, "generate_changelog.py").returncode == 0
    git_changelog(changelog_repository, "add", "CHANGELOG.md")
    before = git_changelog(changelog_repository, "diff", "--cached")
    result = changelog_command(changelog_repository, "run_hook.py", "changelog")
    assert result.returncode == 1
    assert "preview is stale" in result.stdout
    assert git_changelog(changelog_repository, "diff", "--cached") == before
    assert fragment.read_text(encoding="utf-8") == "Uncommitted change.\n"


def test_changelog_hook_uses_staged_fragment_preview_and_renderer(changelog_repository: Path) -> None:
    """Partial staging validates indexed content and preserves every unstaged edit."""
    fragment = changelog_repository / "changelog.d/125.fixed.md"
    fragment.write_text("Staged change.\n", encoding="utf-8")
    assert changelog_command(changelog_repository, "generate_changelog.py").returncode == 0
    git_changelog(changelog_repository, "add", "changelog.d/125.fixed.md", "CHANGELOG.md")
    fragment.write_text("", encoding="utf-8")
    preview = changelog_repository / "CHANGELOG.md"
    preview.write_text("Unstaged preview edit", encoding="utf-8")
    renderer = changelog_repository / "tools/generate_changelog.py"
    renderer.write_text('raise RuntimeError("Unstaged renderer")\n', encoding="utf-8")
    before = git_changelog(changelog_repository, "diff", "--cached")
    result = changelog_command(changelog_repository, "run_hook.py", "changelog")
    assert result.returncode == 0, result.stdout + result.stderr
    assert fragment.read_text(encoding="utf-8") == ""
    assert preview.read_text(encoding="utf-8") == "Unstaged preview edit"
    assert "Unstaged renderer" in renderer.read_text(encoding="utf-8")
    assert git_changelog(changelog_repository, "diff", "--cached") == before


@pytest.mark.parametrize("fault", ["empty", "invalid-name"])
def test_changelog_hook_rejects_invalid_staged_fragment(changelog_repository: Path, fault: str) -> None:
    """Invalid index content fails even when working-directory content looks valid."""
    name = "125.fixed.md" if fault == "empty" else "invalid.md"
    fragment = changelog_repository / "changelog.d" / name
    fragment.write_text("" if fault == "empty" else "Invalid filename", encoding="utf-8")
    git_changelog(changelog_repository, "add", f"changelog.d/{name}")
    fragment.write_text("Valid unstaged content", encoding="utf-8")
    result = changelog_command(changelog_repository, "run_hook.py", "changelog")
    assert result.returncode != 0
    assert ("Empty changelog" if fault == "empty" else "Invalid changelog fragment") in result.stderr
    assert fragment.read_text(encoding="utf-8") == "Valid unstaged content"


@pytest.mark.parametrize("operation", ["delete", "rename"])
def test_changelog_hook_respects_index_deletion_and_rename(changelog_repository: Path, operation: str) -> None:
    """Removed fragment paths stay absent from validation even if they reappear locally."""
    fragment = changelog_repository / "changelog.d/123.fixed.md"
    if operation == "delete":
        git_changelog(changelog_repository, "rm", "changelog.d/123.fixed.md")
    else:
        git_changelog(changelog_repository, "mv", "changelog.d/123.fixed.md", "changelog.d/126.fixed.md")
    assert changelog_command(changelog_repository, "generate_changelog.py").returncode == 0
    git_changelog(changelog_repository, "add", "CHANGELOG.md")
    fragment.write_text("", encoding="utf-8")
    before = git_changelog(changelog_repository, "diff", "--cached")
    result = changelog_command(changelog_repository, "run_hook.py", "changelog")
    assert result.returncode == 0, result.stdout + result.stderr
    assert fragment.read_text(encoding="utf-8") == ""
    assert git_changelog(changelog_repository, "diff", "--cached") == before


@pytest.mark.skipif(find_spec("pre_commit") is None, reason="Real pre-commit integration runs in Code quality.")
def test_pre_commit_changelog_preserves_untracked_and_unstaged_files(changelog_repository: Path) -> None:
    """Exercise staged-only validation through pre-commit's real stash and restoration."""
    root = Path(__file__).resolve().parents[1]
    shutil.copy(root / ".pre-commit-config.yaml", changelog_repository / ".pre-commit-config.yaml")
    prepare_hook_environment(changelog_repository)
    git_changelog(changelog_repository, "add", ".pre-commit-config.yaml")
    untracked = changelog_repository / "changelog.d/unfinished.txt"
    untracked.write_text("Untracked draft", encoding="utf-8")
    tracked = changelog_repository / "changelog.d/123.fixed.md"
    tracked.write_text("", encoding="utf-8")
    before = git_changelog(changelog_repository, "diff", "--cached")
    result = subprocess.run(
        [sys.executable, "-m", "pre_commit", "run", "changelog"],
        cwd=changelog_repository,
        env={**os.environ, "PRE_COMMIT_HOME": str(changelog_repository / "cache")},
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert untracked.read_text(encoding="utf-8") == "Untracked draft"
    assert tracked.read_text(encoding="utf-8") == ""
    assert git_changelog(changelog_repository, "diff", "--cached") == before


def test_changelog_hook_materializes_sparse_index_files(changelog_repository: Path) -> None:
    """Changelog files outside a sparse checkout still participate in staged validation."""
    git_changelog(
        changelog_repository,
        "-c",
        "user.name=Hook Test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "--no-verify",
        "-m",
        "Commit fixture inputs",
    )
    git_changelog(changelog_repository, "sparse-checkout", "set", "--cone", "tools")
    assert not (changelog_repository / "changelog.d").exists()
    config = changelog_repository / "pyproject.toml"
    config.write_text(config.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    git_changelog(changelog_repository, "add", "pyproject.toml")
    flags = git_changelog(changelog_repository, "ls-files", "-v")
    result = changelog_command(changelog_repository, "run_hook.py", "changelog")
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (changelog_repository / "changelog.d").exists()
    assert git_changelog(changelog_repository, "ls-files", "-v") == flags
