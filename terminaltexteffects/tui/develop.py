"""Find the effect modules in the effect directories, and import them again when their files change.

The interface lists every module in the built-in, user, and development effect directories. A module that cannot be
imported, or whose command is already taken, is listed by its file name with the reason. `DevEffects.scan` compares
each file's modification time and size with the last scan and imports changed modules from their source, so an edit
shows up without restarting.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import sys
import traceback
import typing
from pathlib import Path

from terminaltexteffects.tui import options

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Collection, Mapping, Sequence
    from types import ModuleType

    from terminaltexteffects.engine.base_config import BaseConfig
    from terminaltexteffects.engine.base_effect import BaseEffect

MODULE_PREFIX = "_tte_dev_"
"""Prefix of the module names development effects are imported under, as the command line imports them."""

EffectResources = tuple[type["BaseEffect"], type["BaseConfig"]]


@dataclasses.dataclass
class DevEffect:
    """One module in the development directory."""

    path: Path
    signature: tuple[int, int]
    """Modification time and size of the file when it was imported."""
    module_name: str
    """Name the module is imported under."""
    command: str | None = None
    """Command the module registers, or `None` if it could not be imported."""
    resources: EffectResources | None = None
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
    """The effect modules in one or more directories, imported again when they change."""

    def __init__(
        self,
        directories: Path | Sequence[tuple[Path, str]],
        reserved: Collection[str] = (),
        imported: Mapping[Path, tuple[str, EffectResources]] | None = None,
        check_name: Callable[[Path, str], None] | None = None,
    ) -> None:
        """Initialize an empty set of the modules in `directories`.

        Args:
            directories (Path | Sequence[tuple[Path, str]]): Directories to watch, in priority order, each with the
                prefix of the module names its files are imported under. A single path is a development directory.
            reserved (Collection[str]): Commands that belong to effects outside the directories.
            imported (Mapping[Path, tuple[str, EffectResources]] | None): Modules the command line already imported,
                by file, with their command and classes. The first scan lists them without importing them again.
            check_name (Callable[[Path, str], None] | None): Called with the file and module name before a module from
                a directory with no prefix is imported. It raises if the name belongs to another module, which is
                then listed as broken rather than replaced.

        """
        self.directories = [(directories, MODULE_PREFIX)] if isinstance(directories, Path) else list(directories)
        self._reserved = set(reserved)
        self._imported = dict(imported or {})
        self._check_name = check_name
        self.effects: dict[Path, DevEffect] = {}
        """Each module, by file path, in directory order and then file name order."""

    def scan(self) -> dict[Path, str | None]:
        """Import new and changed modules, and forget deleted ones.

        Returns:
            dict[Path, str | None]: The modules that were imported again or whose listing changed, mapped to the
                names they were listed under before, or `None` for new modules. A deleted module is no longer in
                `effects`.

        """
        before = {path: (effect.name, effect.state) for path, effect in self.effects.items()}
        found: dict[Path, tuple[tuple[int, int], str, bool]] = {}
        for directory, prefix in self.directories:
            try:
                paths = sorted(directory.glob("*.py"))
            except OSError:
                paths = []
            for path in paths:
                if path.name == "__init__.py" or path in found:
                    continue
                try:
                    stat = path.stat()
                except OSError:
                    continue
                found[path] = ((stat.st_mtime_ns, stat.st_size), prefix + path.stem, not prefix)
        effects: dict[Path, DevEffect] = {}
        imported: set[Path] = set()
        for path, (signature, module_name, bare) in found.items():
            effect = self.effects.get(path)
            if effect is None and path in self._imported:
                command, resources = self._imported.pop(path)
                effect = DevEffect(path, signature, module_name, command, resources)
            elif effect is None or effect.signature != signature:
                effect = _load(path, signature, module_name, self._check_name if bare else None)
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

    def playable(self) -> dict[str, EffectResources]:
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
        """Return `file:line` of the innermost frame of `error`'s traceback in a watched effect module."""
        paths = {path.resolve() for path in self.effects}
        location = None
        for frame in traceback.extract_tb(error.__traceback__):
            path = Path(frame.filename)
            if path.resolve() in paths:
                location = f"{path.name}:{frame.lineno}"
        return location


def _load(
    path: Path,
    signature: tuple[int, int],
    module_name: str,
    check_name: Callable[[Path, str], None] | None = None,
) -> DevEffect:
    """Import the module at `path` from its source as `module_name` and return its listing.

    `check_name`, if given, is called first and may raise to refuse the name.
    """
    effect = DevEffect(path, signature, module_name)
    previous = sys.modules.get(module_name)
    try:
        if check_name is not None:
            check_name(path, module_name)
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
        _bind_to_parent(module_name, module)
        exec(code, module.__dict__)  # noqa: S102
        get_resources = getattr(module, "get_effect_resources", None)
        if get_resources is None:
            effect.error = "The module has no get_effect_resources() function."
            return effect
        command, effect_class, config_class = get_resources()
        # Reading the options checks the config class as the interface will use it, so a mistake shows here.
        options.option_fields(config_class)
        if not isinstance(effect_class, type):
            msg = f"get_effect_resources() returned {effect_class!r} as the effect class."
            raise TypeError(msg)  # noqa: TRY301
        parser_command = getattr(getattr(config_class, "parser_spec", None), "name", None)
        if not isinstance(command, str) or not command or command != parser_command:
            # The command line refuses such a module, so the interface does too.
            msg = (
                f"get_effect_resources() returned the command {command!r}, "
                f"but the parser command is {parser_command!r}."
            )
            raise ValueError(msg)  # noqa: TRY301
        effect.command = command
        effect.resources = (effect_class, config_class)
    except (Exception, SystemExit) as error:  # noqa: BLE001
        if previous is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous
        _bind_to_parent(module_name, previous)
        effect.error = format_error(error, path)
    return effect


def _bind_to_parent(module_name: str, module: ModuleType | None) -> None:
    """Set `module` as the attribute of its parent package, as an import does, or remove it for `None`.

    `import package.name as name` reads the parent package's attribute, so a module imported again must replace it.
    """
    parent_name, _, child = module_name.rpartition(".")
    parent = sys.modules.get(parent_name) if parent_name else None
    if parent is None:
        return
    if module is not None:
        setattr(parent, child, module)
    elif hasattr(parent, child):
        delattr(parent, child)


def format_error(error: BaseException, path: Path) -> str:
    """Return the traceback of `error`, starting at the first frame in `path`, for display."""
    exception = traceback.TracebackException.from_exception(error)
    stack = list(exception.stack)
    first = next((index for index, frame in enumerate(stack) if Path(frame.filename) == path), None)
    if first is None:
        return "".join(exception.format_exception_only()).rstrip()
    exception.stack = traceback.StackSummary.from_list(stack[first:])
    return "".join(exception.format()).rstrip()
