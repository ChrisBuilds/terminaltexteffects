"""Ensure missing or conditional uv dependencies cannot silently pass security review."""

from __future__ import annotations

import sys

import pytest

from tools import check_dependency_review as review


def test_universal_lock_retains_conditional_versions() -> None:
    """Registry alternatives remain covered regardless of host Python and dependency group."""
    if sys.version_info < (3, 11):
        pytest.importorskip("tomli")
    text = """
[[package]]
name = "example_pkg"
version = "1.0"
source = {registry = "https://pypi.org/simple"}
resolution-markers = ["python_full_version < '3.10'"]
[[package]]
name = "example-pkg"
version = "2.0"
source = {registry = "https://pypi.org/simple"}
resolution-markers = ["python_full_version >= '3.10'"]
[[package]]
name = "terminaltexteffects"
version = "0.15.0"
source = {editable = "."}
"""
    assert review.lock_pairs(text) == {("example-pkg", "1.0"), ("example-pkg", "2.0")}


def test_unsupported_head_dependency_fails() -> None:
    """New VCS/path dependencies require explicit review rather than claiming registry coverage."""
    if sys.version_info < (3, 11):
        pytest.importorskip("tomli")
    text = '[[package]]\nname="external"\nversion="1"\nsource={git="https://example.com/pkg"}\n'
    with pytest.raises(ValueError, match="non-registry"):
        review.lock_pairs(text)
    assert review.lock_pairs(text, require_registry=False) == set()


def test_complete_review_matches_transitive_conditional_pairs() -> None:
    """Both removals and every added alternative must be present; names normalize consistently."""
    changes = [
        {"change_type": kind, "manifest": "uv.lock", "ecosystem": "pip", "name": "Example_Pkg", "version": version}
        for kind, version in [("removed", "1"), ("added", "2"), ("added", "3")]
    ]
    assert review.missing_changes({("example-pkg", "1")}, {("example-pkg", "2"), ("example-pkg", "3")}, changes) == []
    assert review.missing_changes(
        {("example-pkg", "1")}, {("example-pkg", "2"), ("example-pkg", "3")}, changes[:-1]
    ) == ["Missing added uv.lock pair: example-pkg==3"]


def test_empty_or_wrong_manifest_cannot_hide_lock_changes() -> None:
    """An empty snapshot or changes attributed to another manifest cannot satisfy uv review."""
    for changes in [[], [{"manifest": "requirements.txt", "ecosystem": "pip"}]]:
        assert len(review.missing_changes({("old", "1")}, {("new", "2")}, changes)) == 2
    assert review.missing_changes({("old", "1")}, {("old", "1")}, []) == []


@pytest.mark.parametrize("changes", [None, {}, [None], [{"manifest": "uv.lock", "ecosystem": "pip"}]])
def test_malformed_output_fails(changes: object) -> None:
    """Malformed API data must fail closed rather than look like a clean comparison."""
    with pytest.raises((KeyError, TypeError, ValueError)):
        review.missing_changes(set(), set(), changes)


@pytest.mark.parametrize(("payload", "expected"), [("[]", 0), ("", 1), ("null", 1)])
def test_cli_missing_output_fails(monkeypatch: pytest.MonkeyPatch, payload: str, expected: int) -> None:
    """No lock changes permit an empty array, but absent/malformed action output must fail."""
    monkeypatch.setattr(sys, "argv", ["check_dependency_review.py", "--base", "base", "--head", "head"])
    monkeypatch.setenv("DEPENDENCY_CHANGES", payload)
    monkeypatch.setattr(review, "revision_lock", lambda _root, _revision: "package=[]\n")
    assert review.main() == expected
