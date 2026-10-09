"""Verify documentation exemptions cannot hide changes requiring compatibility tests."""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from tools import classify_ci
from tools.generate_changelog import git_output

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """Create a baseline with prose and Python source for realistic Git comparisons."""
    (tmp_path / "README.md").write_text("Introduction\n")
    (tmp_path / "original.py").write_text("VALUE = 1\n")
    for args in (
        ("init", "-b", "main"),
        ("config", "user.email", "test@example.com"),
        ("config", "user.name", "CI Test"),
        ("add", "."),
        ("commit", "-m", "Baseline"),
        ("checkout", "-b", "feature"),
    ):
        git_output(tmp_path, *args)
    return tmp_path


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("README.md", (False, True)),
        ("docs/guide.md", (False, True)),
        ("docs/img/demo.gif", (False, True)),
        (".github/CI.md", (False, True)),
        ("changelog.d/84.skip.md", (False, True)),
        ("terminaltexteffects/engine/motion.py", (True, True)),
        ("terminaltexteffects/effects/effect_wipe.py", (True, True)),
        ("terminaltexteffects/utils/graphics.pyi", (True, True)),
        ("terminaltexteffects/completions/tte.bash", (True, True)),
        ("tests/test_example.py", (True, False)),
        ("pyproject.toml", (True, True)),
        ("uv.lock", (True, True)),
        ("default.nix", (True, True)),
        ("flake.nix", (True, True)),
        ("flake.lock", (True, True)),
        ("tools/check_nix.sh", (True, False)),
        (".github/workflows/ci.yml", (True, True)),
        (".github/workflows/docs.yml", (True, True)),
        (".github/workflows/unrelated.yml", (True, False)),
        (".github/workflows/example.md", (True, False)),
        ("docs/script.py", (True, True)),
        ("docs/stylesheets/extra.css", (True, True)),
        ("tools/example.py", (True, False)),
        ("changelog.d/template.md.jinja", (True, False)),
        ("mkdocs.yml", (True, True)),
        ("overrides/main.html", (True, True)),
        ("overrides/assets/style.css", (True, True)),
        ("unknown-file", (True, False)),
    ],
)
def test_changed_paths_select_required_work(repository: Path, name: str, expected: tuple[bool, bool]) -> None:
    """Only explicitly recognized documentation paths may avoid the Python matrix."""
    path = repository / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("Updated content\n")
    git_output(repository, "add", ".")
    git_output(repository, "commit", "-m", "Change a file")
    assert classify_ci.classify_changes(repository, "main") == expected


def test_deleted_source_and_rename_into_docs_require_tests(repository: Path) -> None:
    """Source deletion cannot be hidden by renaming it to a documentation extension."""
    git_output(repository, "mv", "original.py", "notes.md")
    git_output(repository, "commit", "-m", "Rename source to prose")
    assert classify_ci.classify_changes(repository, "main") == (True, True)


def test_deleted_documentation_is_still_a_documentation_change(repository: Path) -> None:
    """Documentation deletions need link validation even when no prose files are added."""
    git_output(repository, "rm", "README.md")
    git_output(repository, "commit", "-m", "Remove introduction")
    assert classify_ci.classify_changes(repository, "main") == (False, True)


@pytest.mark.parametrize("base", [None, "0" * 40])
def test_manual_or_new_branch_runs_request_complete_validation(repository: Path, base: str | None) -> None:
    """Manual dispatch and missing push history must not silently omit tests."""
    assert classify_ci.classify_changes(repository, base) == (True, True)


def test_missing_revision_fails_instead_of_exempting_tests(repository: Path) -> None:
    """Invalid history stops CI rather than producing a successful documentation exemption."""
    with pytest.raises(subprocess.CalledProcessError):
        classify_ci.classify_changes(repository, "missing-base")


def test_empty_diff_selects_no_additional_work(repository: Path) -> None:
    """An unchanged revision requires neither test execution nor another docs build."""
    assert classify_ci.classify_changes(repository, "HEAD") == (False, False)


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [([], "run_tests=true\nbuild_docs=true\n"), (["--base", "main"], "run_tests=false\nbuild_docs=true\n")],
)
def test_cli_emits_github_outputs(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    arguments: list[str],
    expected: str,
) -> None:
    """Manual and documentation runs emit the string booleans consumed by workflow conditions."""
    (repository / "README.md").write_text("Updated introduction\n")
    git_output(repository, "add", ".")
    git_output(repository, "commit", "-m", "Update documentation")
    monkeypatch.setattr(classify_ci, "__file__", str(repository / "tools" / "classify_ci.py"))
    monkeypatch.setattr(sys, "argv", ["classify_ci.py", *arguments])
    assert classify_ci.main() == 0
    assert capsys.readouterr().out == expected


@pytest.mark.parametrize("source", ["terminaltexteffects/engine/motion.py", "pyproject.toml", "uv.lock"])
@pytest.mark.parametrize("destination", [None, "tests/renamed.py"])
def test_removed_docs_inputs_still_build_docs(repository: Path, source: str, destination: str | None) -> None:
    """Removing or moving API/dependency inputs cannot suppress docs without a Markdown fragment."""
    path = repository / source
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("Original content\n")
    git_output(repository, "checkout", "main")
    git_output(repository, "add", ".")
    git_output(repository, "commit", "-m", "Add documentation input")
    git_output(repository, "checkout", "feature")
    git_output(repository, "merge", "main", "--ff-only")
    if destination is None:
        git_output(repository, "rm", source)
    else:
        (repository / destination).parent.mkdir(parents=True)
        git_output(repository, "mv", source, destination)
    git_output(repository, "commit", "-m", "Remove or move documentation input")
    assert classify_ci.classify_changes(repository, "main") == (True, True)


def test_rename_into_runtime_requires_docs_without_fragment(repository: Path) -> None:
    """A rename's destination can introduce an API docs input even when its source is unrelated."""
    target = repository / "terminaltexteffects/utils"
    target.mkdir(parents=True)
    git_output(repository, "mv", "original.py", "terminaltexteffects/utils/example.py")
    git_output(repository, "commit", "-m", "Move code into runtime package")
    assert classify_ci.classify_changes(repository, "main") == (True, True)


def test_main_only_docs_change_does_not_affect_branch_selection(repository: Path) -> None:
    """Compare from merge-base so unrelated main docs updates do not trigger branch work."""
    git_output(repository, "checkout", "main")
    (repository / "README.md").write_text("New main introduction\n")
    git_output(repository, "add", ".")
    git_output(repository, "commit", "-m", "Update main docs")
    git_output(repository, "checkout", "feature")
    (repository / "original.py").write_text("VALUE = 2\n")
    git_output(repository, "add", ".")
    git_output(repository, "commit", "-m", "Update unrelated tool")
    assert classify_ci.classify_changes(repository, "main") == (True, False)
