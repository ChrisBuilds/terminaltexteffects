"""Tests for finding development effects and importing them again when they change."""

from __future__ import annotations

import asyncio
import os
import sys
from typing import TYPE_CHECKING

import pytest
from rich.text import Text
from textual.widgets import Button, Checkbox, OptionList, Static

from terminaltexteffects.__main__ import build_parser
from terminaltexteffects.effects.effect_wipe import Wipe
from terminaltexteffects.tui.app import TTEApp
from terminaltexteffects.tui.develop import DevEffects

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

    from textual.pilot import Pilot

PROTOTYPE = """from terminaltexteffects.effects.effect_wipe import Wipe, WipeConfig

SPEED = {speed}

def get_effect_resources():
    return "{command}", Wipe, WipeConfig
"""


def _write(path: Path, text: str) -> None:
    """Write `text` to `path` with a new modification time, as an editor saving the file does."""
    previous = path.stat().st_mtime_ns if path.exists() else 0
    path.write_text(text)
    os.utime(path, ns=(previous + 1_000_000, previous + 1_000_000))


def test_scan_lists_playable_and_broken_modules(tmp_path: Path) -> None:
    """Playable modules are listed by command, and broken ones by file name with the reason."""
    _write(tmp_path / "effect_prototype.py", PROTOTYPE.format(speed=1, command="prototype"))
    _write(tmp_path / "effect_broken.py", "def broken(:\n")
    _write(tmp_path / "helper.py", "VALUE = 1\n")
    _write(tmp_path / "__init__.py", "")
    development = DevEffects(tmp_path, reserved={"wipe"})
    assert development.scan() == {
        tmp_path / "effect_broken.py": None,
        tmp_path / "effect_prototype.py": None,
        tmp_path / "helper.py": None,
    }
    assert development.playable() == {"prototype": (Wipe, development.playable()["prototype"][1])}
    broken = development.broken()
    assert set(broken) == {"effect_broken.py", "helper.py"}
    assert "SyntaxError" in broken["effect_broken.py"]
    assert "get_effect_resources" in broken["helper.py"]
    assert development.scan() == {}


def test_scan_imports_changed_modules_again(tmp_path: Path) -> None:
    """An edit that keeps the file's size is imported from the new source."""
    path = tmp_path / "effect_prototype.py"
    _write(path, PROTOTYPE.format(speed=1, command="prototype"))
    development = DevEffects(tmp_path)
    development.scan()
    assert sys.modules["_tte_dev_effect_prototype"].SPEED == 1
    _write(path, PROTOTYPE.format(speed=2, command="prototype"))
    assert development.scan() == {path: "prototype"}
    assert sys.modules["_tte_dev_effect_prototype"].SPEED == 2


def test_broken_module_is_listed_again_once_fixed(tmp_path: Path) -> None:
    """A module that raises while importing is red until it imports, then listed by its command."""
    path = tmp_path / "effect_prototype.py"
    _write(path, PROTOTYPE.format(speed=1, command="prototype") + "raise RuntimeError('unfinished')\n")
    development = DevEffects(tmp_path)
    development.scan()
    error = development.broken()["effect_prototype.py"]
    assert "RuntimeError: unfinished" in error
    assert 'File "' in error
    _write(path, PROTOTYPE.format(speed=1, command="prototype"))
    assert development.scan() == {path: "effect_prototype.py"}
    assert list(development.playable()) == ["prototype"]
    assert development.broken() == {}
    assert development.path_of("prototype") == path


def test_taken_commands_are_reported(tmp_path: Path) -> None:
    """A module cannot take a built-in command, or one an earlier development module uses."""
    _write(tmp_path / "effect_a.py", PROTOTYPE.format(speed=1, command="same"))
    _write(tmp_path / "effect_b.py", PROTOTYPE.format(speed=1, command="same"))
    _write(tmp_path / "effect_c.py", PROTOTYPE.format(speed=1, command="wipe"))
    development = DevEffects(tmp_path, reserved={"wipe"})
    development.scan()
    assert list(development.playable()) == ["same"]
    assert set(development.broken()) == {"effect_b.py", "effect_c.py"}
    (tmp_path / "effect_a.py").unlink()
    changed = development.scan()
    assert changed == {tmp_path / "effect_a.py": "same", tmp_path / "effect_b.py": "effect_b.py"}
    assert list(development.playable()) == ["same"]
    assert development.path_of("same") == tmp_path / "effect_b.py"


def test_location_names_the_development_file(tmp_path: Path) -> None:
    """Errors raised from a development module are located in its file."""
    path = tmp_path / "effect_prototype.py"
    _write(path, PROTOTYPE.format(speed=1, command="prototype") + "\ndef fail():\n    raise ValueError('bad')\n")
    development = DevEffects(tmp_path)
    development.scan()
    with pytest.raises(ValueError, match="bad") as raised:
        sys.modules["_tte_dev_effect_prototype"].fail()
    assert development.location(raised.value) == "effect_prototype.py:9"


APP_PROTOTYPE = """from dataclasses import dataclass
from terminaltexteffects.effects.effect_wipe import Wipe, WipeConfig
from terminaltexteffects.utils import argutils

@dataclass
class PrototypeConfig(WipeConfig):
    parser_spec: argutils.ParserSpec = argutils.ParserSpec(
        name="prototype", help="Prototype", description="Prototype", epilog=""
    )

def get_effect_resources():
    return "prototype", Wipe, PrototypeConfig
"""


def _run(app: TTEApp, script: Callable[[TTEApp, Pilot[None]], Awaitable[None]]) -> None:
    async def main() -> None:
        async with app.run_test(size=(100, 34)) as pilot:
            await pilot.pause()
            await script(app, pilot)

    asyncio.run(main())


def test_app_lists_broken_effects_and_plays_them_once_fixed(tmp_path: Path) -> None:
    """A broken module is red and shows its error, then plays with Auto-replay once its file is fixed."""
    path = tmp_path / "effect_prototype.py"
    _write(path, APP_PROTOTYPE + "raise RuntimeError('unfinished')\n")
    _, effects = build_parser(include_user_effects=False)
    development = DevEffects(tmp_path, effects)

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        effect_list = app.query_one("#effects", OptionList)
        names = app._effect_names()
        assert "effect_prototype.py" in names
        assert effect_list.option_count == len(effects) + 1
        prompt = effect_list.get_option_at_index(names.index("effect_prototype.py")).prompt
        assert isinstance(prompt, Text)
        assert prompt.style
        effect_list.highlighted = names.index("effect_prototype.py")
        await pilot.pause()
        assert app.effect_name == "effect_prototype.py"
        assert "unfinished" in str(app.query_one("#options").border_subtitle)
        await pilot.press("f5")
        stage = app.query_one("#stage")
        assert stage.has_class("-import-error")
        assert app.query_one("#step_back", Button).disabled
        assert "RuntimeError: unfinished" in str(app.query_one("#import-error-text", Static).render())
        app.query_one("#auto-replay", Checkbox).value = True
        await pilot.pause()

        _write(path, APP_PROTOTYPE)
        await app._check_development()
        await pilot.pause(0.5)
        assert app.effect_name == "prototype"
        assert not stage.has_class("-import-error")
        assert app.state in {"playing", "finished"}
        assert str(effect_list.get_option_at_index(app._listed.index("prototype")).prompt) == "prototype"

        # Edited options are kept across edits of the file.
        app._values["prototype"] = {"wipe_delay": 3, "removed_option": 1}
        _write(path, APP_PROTOTYPE + "\n")
        await app._check_development()
        await pilot.pause()
        assert app._values["prototype"] == {"wipe_delay": 3}

        path.unlink()
        await app._check_development()
        await pilot.pause()
        assert app.effect_name in effects
        assert app.state == "editing"

    _run(TTEApp(effects, "Hello", effect="effect_prototype.py", development=development), script)


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        ("import sys\nsys.exit(2)\n", "SystemExit"),
        (
            (
                "from terminaltexteffects.effects.effect_wipe import Wipe\n"
                "class Config: pass\n"
                "def get_effect_resources():\n    return 'odd', Wipe, Config\n"
            ),
            "TypeError",
        ),
    ],
)
def test_modules_that_exit_or_return_bad_classes_are_broken(tmp_path: Path, body: str, reason: str) -> None:
    """A module that exits while importing, or whose config class is not usable, is listed as broken."""
    _write(tmp_path / "effect_odd.py", body)
    development = DevEffects(tmp_path)
    development.scan()
    assert development.playable() == {}
    assert reason in development.broken()["effect_odd.py"]
