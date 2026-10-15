"""Tests for saving and restoring the TUI session file."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from terminaltexteffects.tui import session

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_session_round_trips(tmp_path: Path) -> None:
    """A saved session should load back unchanged."""
    path = tmp_path / "config" / "session.json"
    saved = session.Session(
        "wipe",
        {"wipe": {"wipe_delay": "3"}},
        "\x1b[31mhi\x1b[0m",
        "text.txt",
        loop=True,
        show_options=False,
    )

    session.save_session(path, saved)

    assert session.load_session(path) == saved
    assert not path.with_suffix(".tmp").exists()


def test_invalid_session_files_are_ignored(tmp_path: Path) -> None:
    """Missing, unreadable, or wrong-version files should load as no session, and bad fields should be dropped."""
    path = tmp_path / "session.json"
    assert session.load_session(path) is None
    path.write_text("not json", encoding="utf-8")
    assert session.load_session(path) is None
    path.write_text(json.dumps({"version": 99}), encoding="utf-8")
    assert session.load_session(path) is None
    path.write_text(
        json.dumps({"version": session.SESSION_VERSION, "effect": 3, "values": {"wipe": "x"}, "loop": "yes"}),
        encoding="utf-8",
    )
    assert session.load_session(path) == session.Session()


def test_oversized_text_is_not_saved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Text longer than the limit should be left out of the session file."""
    monkeypatch.setattr(session, "MAX_SESSION_TEXT", 4)
    path = tmp_path / "session.json"
    session.save_session(path, session.Session(text="too long"))
    loaded = session.load_session(path)
    assert loaded is not None
    assert loaded.text is None


def test_default_path_follows_xdg_config_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The session file should live under `XDG_CONFIG_HOME` when it is an absolute path."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert session.default_session_path() == tmp_path / "terminaltexteffects" / "tui_session.json"
    monkeypatch.setenv("XDG_CONFIG_HOME", "relative")
    assert session.default_session_path().parts[-3:] == (".config", "terminaltexteffects", "tui_session.json")
