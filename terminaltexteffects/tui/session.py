"""Save and restore the TUI's last session.

The session file keeps the selected effect, changed option values in their command-line spelling, the text with its
input colors, the playback toggles, and which panels are shown. Values are stored as text and parsed again on load,
so a value that is no longer valid, or an effect that is no longer installed, is skipped instead of breaking startup.
This module does not import Textual.
"""

from __future__ import annotations

import json
import os
import typing
from dataclasses import asdict, dataclass, field
from pathlib import Path

SESSION_VERSION = 1
MAX_SESSION_TEXT = 1_000_000
"""Longest text, in characters, kept in the session file."""


def default_session_path() -> Path:
    """Return the session file under the XDG config home, next to the user effects directory."""
    config_home = os.environ.get("XDG_CONFIG_HOME", "")
    config_dir = Path(config_home) if config_home and Path(config_home).is_absolute() else Path.home() / ".config"
    return config_dir / "terminaltexteffects" / "tui_session.json"


@dataclass
class Session:
    """The state restored when the TUI opens.

    Attributes:
        effect (str | None): Selected effect name.
        values (dict[str, dict[str, str]]): Changed option values by scope, then field name, as editor text.
        text (str | None): Text, with input colors as SGR sequences, or `None` when it was too long to keep.
        input_file (str | None): File the text was last opened from or saved to.
        loop (bool): Whether playback loops.
        auto_replay (bool): Whether option changes replay the effect.
        show_effects (bool): Whether the effect list is shown.
        show_options (bool): Whether the options panel is shown.

    """

    effect: str | None = None
    values: dict[str, dict[str, str]] = field(default_factory=dict)
    text: str | None = None
    input_file: str | None = None
    loop: bool = False
    auto_replay: bool = False
    show_effects: bool = True
    show_options: bool = True


def load_session(path: Path) -> Session | None:
    """Return the session saved at `path`, or `None` when there is none or it cannot be read."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("version") != SESSION_VERSION:
        return None
    values = data.get("values")
    return Session(
        effect=_optional_str(data.get("effect")),
        values={
            str(scope): {str(name): str(text) for name, text in fields.items()}
            for scope, fields in (values.items() if isinstance(values, dict) else ())
            if isinstance(fields, dict)
        },
        text=_optional_str(data.get("text")),
        input_file=_optional_str(data.get("input_file")),
        loop=data.get("loop") is True,
        auto_replay=data.get("auto_replay") is True,
        show_effects=data.get("show_effects") is not False,
        show_options=data.get("show_options") is not False,
    )


def save_session(path: Path, session: Session) -> None:
    """Write `session` to `path`, dropping text longer than `MAX_SESSION_TEXT`.

    Raises:
        OSError: If the file cannot be written.

    """
    data: dict[str, typing.Any] = {"version": SESSION_VERSION, **asdict(session)}
    if session.text is not None and len(session.text) > MAX_SESSION_TEXT:
        data["text"] = None
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temporary.replace(path)


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) else None
