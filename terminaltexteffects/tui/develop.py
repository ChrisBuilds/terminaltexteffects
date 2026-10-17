"""Find the effects in a development directory, and import them again when their files change.

The interface lists every module in the directory. A module that cannot be imported, or whose command is already
taken, is listed by its file name with the reason. `DevEffects.scan` compares each file's modification time and size
with the last scan and imports changed modules from their source, so an edit shows up without restarting.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import sys
import traceback
import typing
from pathlib import Path

if typing.TYPE_CHECKING:
    from collections.abc import Collection

    from terminaltexteffects.engine.base_config import BaseConfig
    from terminaltexteffects.engine.base_effect import BaseEffect

MODULE_PREFIX = "_tte_dev_"
"""Prefix of the module names development effects are imported under, as the command line imports them."""


@dataclasses.dataclass
class DevEffect:
    """One module in the development directory."""

    path: Path
    signature: tuple[int, int]
    """Modification time and size of the file when it was imported."""
    command: str | None = None
    """Command the module registers, or `None` if it could not be imported."""
    resources: tuple[type[BaseEffect], type[BaseConfig]] | None = None
    """Effect and config classes, or `None` if the module cannot be played."""
    error: str | None = None
    """Why the module cannot be played, formatted for display, or `None`."""

    @property
    def name(self) -> str:
        """Return the name listed for the module: its command, or its file name if it cannot be played."""
        return self.command if self.error is None and self.command is not None else self.path.name

    @property
    def state(self) -> tuple[object, ...]:
        """Return what the interface shows for the module, to tell whether a scan changed it."""
        return (self.name, self.resources, self.error)


class DevEffects:
    """The effect modules in a development directory, imported again when they change."""

    def __init__(self, directory: Path, reserved: Collection[str] = ()) -> None:
        """Initialize an empty set of the modules in `directory`. Commands in `reserved` belong to other effects."""
        self.directory = directory
        self._reserved = set(reserved)
        self.effects: dict[Path, DevEffect] = {}
        """Each module, by file path, in file name order."""

    def scan(self) -> dict[Path, str | None]:
        """Import new and changed modules, and forget deleted ones.

        Returns:
            dict[Path, str | None]: The modules that were imported again or whose listing changed, mapped to the
                names they were listed under before, or `None` for new modules. A deleted module is no longer in
                `effects`.

        """
        before = {path: (effect.name, effect.state) for path, effect in self.effects.items()}
        found: dict[Path, tuple[int, int]] = {}
        try:
            paths = sorted(self.directory.glob("*.py"))
        except OSError:
            paths = []
        for path in paths:
            if path.name == "__init__.py":
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            found[path] = (stat.st_mtime_ns, stat.st_size)
        effects: dict[Path, DevEffect] = {}
        imported: set[Path] = set()
        for path, signature in found.items():
            effect = self.effects.get(path)
            if effect is None or effect.signature != signature:
                effect = _load(path, signature)
                imported.add(path)
            effects[path] = effect
        self.effects = effects
        self._resolve_commands()
        changed: dict[Path, str | None] = {path: name for path, (name, _) in before.items() if path not in effects}
        for path, effect in effects.items():
            if path not in before:
                changed[path] = None
            elif path in imported or before[path][1] != effect.state:
                changed[path] = before[path][0]
        return changed

    def _resolve_commands(self) -> None:
        """Mark modules whose command another effect already uses. The first file in name order keeps it."""
        taken = set(self._reserved)
        for effect in self.effects.values():
            if effect.command is None:
                continue
            # A module with a command imported, so its only possible problem is a command that is taken.
            if effect.command in taken:
                effect.error = f"The command {effect.command!r} is already used by another effect."
            else:
                effect.error = None
                taken.add(effect.command)

    def playable(self) -> dict[str, tuple[type[BaseEffect], type[BaseConfig]]]:
        """Return the commands of the modules that can be played, with their effect and config classes."""
        return {
            effect.name: effect.resources
            for effect in self.effects.values()
            if effect.error is None and effect.resources is not None
        }

    def broken(self) -> dict[str, str]:
        """Return the file names of the modules that cannot be played, with the reason."""
        return {effect.name: effect.error for effect in self.effects.values() if effect.error is not None}

    def path_of(self, name: str) -> Path | None:
        """Return the file of the module listed as `name`, or `None` if no module is."""
        return next((path for path, effect in self.effects.items() if effect.name == name), None)

    def location(self, error: BaseException) -> str | None:
        """Return `file:line` of the innermost frame of `error`'s traceback in the development directory."""
        directory = self.directory.resolve()
        location = None
        for frame in traceback.extract_tb(error.__traceback__):
            path = Path(frame.filename)
            if path.parent.resolve() == directory:
                location = f"{path.name}:{frame.lineno}"
        return location


def _load(path: Path, signature: tuple[int, int]) -> DevEffect:
    """Import the module at `path` from its source and return its listing."""
    effect = DevEffect(path, signature)
    module_name = MODULE_PREFIX + path.stem
    previous = sys.modules.get(module_name)
    try:
        source = path.read_bytes()
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None:
            msg = f"Unable to create a module specification for {path}"
            raise ImportError(msg)  # noqa: TRY301
        module = importlib.util.module_from_spec(spec)
        # The source is compiled directly, because a cached bytecode file can be stale after a quick edit that keeps
        # the file's size and whole-second modification time.
        code = compile(source, str(path), "exec", dont_inherit=True)
        sys.modules[module_name] = module
        exec(code, module.__dict__)  # noqa: S102
        get_resources = getattr(module, "get_effect_resources", None)
        if get_resources is None:
            effect.error = "The module has no get_effect_resources() function."
            return effect
        command, effect_class, config_class = get_resources()
        effect.command = str(command)
        effect.resources = (effect_class, config_class)
    except (Exception, SystemExit) as error:  # noqa: BLE001
        if previous is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous
        effect.error = format_error(error, path)
    return effect


def format_error(error: BaseException, path: Path) -> str:
    """Return the traceback of `error`, starting at the first frame in `path`, for display."""
    exception = traceback.TracebackException.from_exception(error)
    stack = list(exception.stack)
    first = next((index for index, frame in enumerate(stack) if Path(frame.filename) == path), None)
    if first is None:
        return "".join(exception.format_exception_only()).rstrip()
    exception.stack = traceback.StackSummary.from_list(stack[first:])
    return "".join(exception.format()).rstrip()
