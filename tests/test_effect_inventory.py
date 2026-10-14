"""Verify shipped effect promotion fails for missing registration, docs, navigation, or tests."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from terminaltexteffects.effects import effect_wipe
from tools import check_effect_inventory as inventory
from tools.perf.benchmark_effects import INPUT_PRESET_NAMES


@pytest.fixture
def promoted_effect(tmp_path: Path) -> Path:
    """Create a minimal complete effect whose command differs from its module suffix."""
    files = {
        "terminaltexteffects/effects/effect_random_sequence.py": "# effect\n",
        "docs/effects/randomsequence.md": "# Random Sequence\n",
        "tests/effects_tests/test_randomsequence.py": "def test_behavior():\n    assert True\n",
        "mkdocs.yml": (
            "extra:\n  revision: !ENV [REVISION, '']\nnav:\n  - Effects:\n    - Demo: effects/randomsequence.md\n"
        ),
    }
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return tmp_path


def problems(root: Path, navigation: set[str] | None = None) -> list[str]:
    """Check one known registered command independently of the real runtime parser."""
    return inventory.check_inventory(
        root,
        {"effect_random_sequence": "randomsequence"},
        {"effects/randomsequence.md"} if navigation is None else navigation,
    )


def test_complete_inventory(promoted_effect: Path) -> None:
    """Different module and command spellings remain supported."""
    assert problems(promoted_effect) == []


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("docs/effects/randomsequence.md", "missing or empty"),
        ("tests/effects_tests/test_randomsequence.py", "missing tests"),
        ("terminaltexteffects/effects/effect_random_sequence.py", "no shipped effect module"),
    ],
)
def test_missing_resource(promoted_effect: Path, name: str, message: str) -> None:
    """Removing a required promotion resource fails with an actionable diagnostic."""
    (promoted_effect / name).unlink()
    assert any(message in item for item in problems(promoted_effect))


@pytest.mark.parametrize("content", ["", "  \n"])
def test_empty_doc(promoted_effect: Path, content: str) -> None:
    """An empty placeholder page does not satisfy documentation presence."""
    (promoted_effect / "docs/effects/randomsequence.md").write_text(content)
    assert any("missing or empty" in item for item in problems(promoted_effect))


@pytest.mark.parametrize("content", ["# tests pending\n", "def helper():\n    pass\n", "def invalid(:\n"])
def test_missing_or_invalid_tests(promoted_effect: Path, content: str) -> None:
    """A placeholder, helper-only file, or syntax error cannot satisfy permanent tests."""
    (promoted_effect / "tests/effects_tests/test_randomsequence.py").write_text(content)
    assert problems(promoted_effect)


def test_unregistered_shipped_prototype(promoted_effect: Path) -> None:
    """A stray development module cannot be hidden by built-in discovery's prototype exclusion."""
    (promoted_effect / "terminaltexteffects/effects/effect_dev.py").write_text("# scratch\n")
    assert any("effect_dev: shipped module is missing" in item for item in problems(promoted_effect))


def test_navigation_label_is_not_a_page(promoted_effect: Path) -> None:
    """A page name in a label or outside nav cannot satisfy its navigation entry."""
    paths = inventory.navigation_paths([{"effects/randomsequence.md": ["effects/other.md"]}])
    assert any("add effects/randomsequence.md" in item for item in problems(promoted_effect, paths))


def test_yaml_navigation_and_custom_tags(promoted_effect: Path) -> None:
    """Read nested nav while ignoring custom tag execution and references elsewhere."""
    pytest.importorskip("yaml", reason="Navigation loader uses the development MkDocs dependency")
    assert inventory.load_navigation(promoted_effect) == {"effects/randomsequence.md"}
    (promoted_effect / "mkdocs.yml").write_text(
        "extra:\n  page: effects/randomsequence.md\nnav:\n  - Intro: index.md\n# effects/randomsequence.md\n"
    )
    assert inventory.load_navigation(promoted_effect) == {"index.md"}
    assert problems(promoted_effect, inventory.load_navigation(promoted_effect))


def test_class_based_tests(promoted_effect: Path) -> None:
    """Permanent tests may use a pytest Test-prefixed class."""
    (promoted_effect / "tests/effects_tests/test_randomsequence.py").write_text(
        "class TestBehavior:\n    def test_frame(self):\n        assert True\n"
    )
    assert problems(promoted_effect) == []


def test_parser_command_resource_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """An effect config registering a different command cannot pass the promotion check."""
    parser = argparse.ArgumentParser()
    parser.add_subparsers().add_parser("different")
    monkeypatch.setattr(
        inventory,
        "build_parser",
        lambda **_kwargs: (
            parser,
            {"wipe": (effect_wipe.Wipe, effect_wipe.WipeConfig)},
        ),
    )
    with pytest.raises(ValueError, match="subcommands disagree"):
        inventory.registered_effects()


def _profile_options(effects: list[str]) -> dict[str, list[str]]:
    """Build Profile workflow options that match `effects` and the harness presets."""
    return {
        "effect": ["all", *effects],
        "input_preset": ["medium + large", *INPUT_PRESET_NAMES, "all presets"],
    }


def test_profile_options_match() -> None:
    """Drop-downs listing every effect and preset in order pass."""
    assert inventory.check_profile_options(_profile_options(["beams", "wipe"]), ["wipe", "beams"]) == []


@pytest.mark.parametrize(
    ("options", "message"),
    [
        (_profile_options(["beams"]), "add wipe"),
        (_profile_options(["beams", "wipe", "gone"]), "remove gone"),
        (_profile_options(["wipe", "beams"]), "keep the options in order"),
        ({"effect": ["all", "beams", "wipe"]}, "`input_preset` options are out of date: add medium + large"),
    ],
)
def test_profile_options_drift(options: dict[str, list[str]], message: str) -> None:
    """Added, removed, or reordered effects and presets fail with an actionable diagnostic."""
    assert any(message in item for item in inventory.check_profile_options(options, ["beams", "wipe"]))


def test_load_profile_options(tmp_path: Path) -> None:
    """Choice options are read from the manual inputs; other inputs are ignored."""
    pytest.importorskip("yaml", reason="Workflow loader uses the development MkDocs dependency")
    workflow = tmp_path / inventory.PROFILE_WORKFLOW
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "on:\n  workflow_dispatch:\n    inputs:\n"
        "      effect:\n        type: choice\n        options: [all, wipe]\n"
        "      seed:\n        type: number\n        default: 1\n"
    )
    assert inventory.load_profile_options(tmp_path) == {"effect": ["all", "wipe"]}
    workflow.write_text("on:\n  push:\n")
    with pytest.raises(TypeError, match="no workflow_dispatch inputs"):
        inventory.load_profile_options(tmp_path)


def test_repository_profile_options_are_current() -> None:
    """The committed Profile workflow lists every shipped effect and harness preset."""
    pytest.importorskip("yaml", reason="Workflow loader uses the development MkDocs dependency")
    root = Path(__file__).resolve().parents[1]
    commands = list(inventory.registered_effects().values())
    assert inventory.check_profile_options(inventory.load_profile_options(root), commands) == []
