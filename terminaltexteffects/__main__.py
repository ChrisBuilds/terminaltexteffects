"""Package entry point for the TerminalTextEffects command line interface."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.machinery
import importlib.util
import math
import os
import pkgutil
import random
import shutil
import sys
import tempfile
import time
import weakref
from contextlib import contextmanager
from dataclasses import dataclass
from functools import partial
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn, cast

import terminaltexteffects.effects
from terminaltexteffects import tui
from terminaltexteffects.engine._recording import (
    RECORDING_SUFFIX,
    RecordingError,
    RecordingHeader,
    RecordingReader,
    RecordingWriter,
)
from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.utils import ansitools, export
from terminaltexteffects.utils.argutils import NonNegativeFloat, NonNegativeInt
from terminaltexteffects.utils.exceptions import EmptyInputError, UnsupportedAnsiSequenceError
from terminaltexteffects.utils.shell_completion import (
    get_completion_instructions,
    get_completion_script,
    parse_completion_shell,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterator
    from importlib.machinery import SourceFileLoader
    from types import ModuleType

    from terminaltexteffects.engine.base_config import BaseConfig
    from terminaltexteffects.engine.base_effect import BaseEffect


_DEV_EFFECT_MODULE_PREFIX = "_tte_dev_"
# User plugin modules registered by this process, which later user plugin discovery may replace.
_USER_PLUGIN_MODULES: weakref.WeakSet[ModuleType] = weakref.WeakSet()
# The module file of each effect command the last `build_parser` call registered.
_EFFECT_FILES: dict[str, Path] = {}


def _user_effects_dir() -> Path:
    """Return the user effects directory under the XDG config home.

    Per the XDG Base Directory specification, an unset, empty, or relative `XDG_CONFIG_HOME`
    falls back to `~/.config`.
    """
    config_home = os.environ.get("XDG_CONFIG_HOME", "")
    config_dir = Path(config_home) if config_home and Path(config_home).is_absolute() else Path.home() / ".config"
    return config_dir / "terminaltexteffects" / "effects"


def _external_effect_files(directory: Path, prefix: str = "") -> Iterator[tuple[Path, str]]:
    """Yield flat external module paths and their module names in deterministic order."""
    for plugin_file in sorted(directory.glob("*.py")):
        if plugin_file.name == "__init__.py":
            continue
        yield plugin_file, prefix + plugin_file.stem


def _load_external_module(plugin_file: Path, module_name: str) -> ModuleType:
    """Load a flat external module without altering the import path.

    If execution fails, `sys.modules` is restored to the entry it held for `module_name` before loading.

    Raises:
        ImportError: If no module specification can be created for `plugin_file`.

    """
    spec = importlib.util.spec_from_file_location(module_name, plugin_file)
    if spec is None or spec.loader is None:
        msg = f"Unable to create a module specification for {plugin_file}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    previous_module = sys.modules.get(module_name)
    sys.modules[module_name] = module
    try:
        # Flat .py paths resolve to SourceFileLoader; typeshed also permits legacy loaders.
        cast("SourceFileLoader", spec.loader).exec_module(module)
    except BaseException:
        _restore_module(module_name, previous_module)
        raise
    return module


def _is_origin_of(origin: object, plugin_file: Path) -> bool:
    """Return whether a module specification origin names `plugin_file`."""
    return isinstance(origin, str) and Path(origin).resolve() == plugin_file.resolve()


def _has_other_module_spec(plugin_file: Path, module_name: str) -> bool:
    """Return whether an import finder resolves `module_name` to a module other than `plugin_file`.

    The plugin's own directory is excluded from the import path search, so a plugin directory placed
    before site-packages on `sys.path` does not hide a same-named installed module.
    """
    plugin_dir = plugin_file.parent.resolve()
    search_path = [
        entry for entry in sys.path if not (isinstance(entry, str) and Path(entry or ".").resolve() == plugin_dir)
    ]
    for finder in sys.meta_path:
        if finder is importlib.machinery.PathFinder:
            spec = importlib.machinery.PathFinder.find_spec(module_name, search_path)
        else:
            find_spec = getattr(finder, "find_spec", None)
            spec = find_spec(module_name, None) if find_spec is not None else None
        if spec is not None and not _is_origin_of(spec.origin, plugin_file):
            return True
    return False


def _check_user_module_name(plugin_file: Path, module_name: str) -> None:
    """Ensure a user plugin's bare module name does not belong to another module.

    A module already in `sys.modules` may be replaced only if it was loaded from `plugin_file` or
    registered as a user plugin, so rediscovery reloads current file contents. Otherwise no import
    finder may resolve the name to another module, searching past `plugin_file` itself when its
    directory is on `sys.path`. A dotted file stem is checked by its top-level name, since
    registering it could otherwise replace an installed submodule.

    Raises:
        ImportError: If `module_name` belongs to a loaded or importable module other than `plugin_file`.

    """
    loaded_module = sys.modules.get(module_name)
    if loaded_module is not None:
        loaded_spec = getattr(loaded_module, "__spec__", None)
        conflict = loaded_module not in _USER_PLUGIN_MODULES and not _is_origin_of(
            getattr(loaded_spec, "origin", None),
            plugin_file,
        )
    elif "." in module_name:
        top_level_name = module_name.partition(".")[0]
        conflict = top_level_name in sys.modules or importlib.util.find_spec(top_level_name) is not None
    else:
        conflict = _has_other_module_spec(plugin_file, module_name)
    if conflict:
        msg = f"Module name {module_name!r} is already used by an installed or loaded module; rename the file"
        raise ImportError(msg)


def _restore_module(module_name: str, previous_module: ModuleType | None) -> None:
    """Restore the `sys.modules` entry that `module_name` held before an external module was loaded."""
    if previous_module is None:
        sys.modules.pop(module_name, None)
    else:
        sys.modules[module_name] = previous_module


def _validate_user_effect_resources(
    resources: object,
    effect_resource_map: dict[str, tuple[type[BaseEffect], type[BaseConfig]]],
) -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Validate user effect resources before any parser state is changed.

    Raises:
        TypeError: If the resources are not an effect command name and two classes.
        ValueError: If the command is empty, already registered, or differs from the parser command.

    """
    if not isinstance(resources, (tuple, list)) or len(resources) != 3:
        msg = "get_effect_resources() must return (effect command, effect class, config class)"
        raise TypeError(msg)
    effect_cmd, effect_class, config_class = resources
    if not isinstance(effect_cmd, str) or not effect_cmd:
        msg = "Effect command must be a non-empty string"
        raise ValueError(msg)
    if not isinstance(effect_class, type) or not isinstance(config_class, type):
        msg = "Effect and config resources must be classes"
        raise TypeError(msg)
    if effect_cmd in effect_resource_map:
        msg = f"Duplicate effect command detected: {effect_cmd}"
        raise ValueError(msg)
    parser_command = getattr(getattr(config_class, "parser_spec", None), "name", None)
    if parser_command != effect_cmd:
        msg = f"Effect command {effect_cmd!r} does not match parser command {parser_command!r}"
        raise ValueError(msg)
    return effect_cmd, effect_class, config_class


def _populate_user_effect_parser(config_class: type[BaseConfig], subparsers: argparse._SubParsersAction) -> None:
    """Populate a user effect's subparser once, removing the partial command if population fails.

    `_populate_parser` creates the subparser before adding options, so a failure part way through
    would otherwise leave a listed command with no registered effect.
    """
    previous_choices = dict(subparsers.choices)
    previous_choice_actions = list(subparsers._choices_actions)
    try:
        config_class._populate_parser(subparsers)
    except BaseException:
        subparsers.choices.clear()
        subparsers.choices.update(previous_choices)
        subparsers._choices_actions[:] = previous_choice_actions
        raise


def _register_user_effect(
    plugin_file: Path,
    module_name: str,
    subparsers: argparse._SubParsersAction,
    effect_resource_map: dict[str, tuple[type[BaseEffect], type[BaseConfig]]],
) -> None:
    """Register one user effect plugin, or skip it with a warning if it fails to load or register."""
    previous_module = sys.modules.get(module_name)
    try:
        _check_user_module_name(plugin_file, module_name)
        module = _load_external_module(plugin_file, module_name)
        _USER_PLUGIN_MODULES.add(module)
        if hasattr(module, "get_effect_resources"):
            effect_cmd, effect_class, config_class = _validate_user_effect_resources(
                module.get_effect_resources(),
                effect_resource_map,
            )
            _populate_user_effect_parser(config_class, subparsers)
            effect_resource_map[effect_cmd] = (effect_class, config_class)
    # SystemExit is a plugin failure here: a plugin calling `sys.exit()` must not end the CLI.
    except (Exception, SystemExit) as exc:  # noqa: BLE001
        _restore_module(module_name, previous_module)
        detail = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
        print(f"Warning: Skipping user effect plugin '{plugin_file}': {detail}", file=sys.stderr)


_MAX_HOLD_SECONDS = 86400.0


def _hold_seconds(arg: str) -> float:
    """Parse a finite `--hold` duration from 0 to `_MAX_HOLD_SECONDS` seconds.

    Raises:
        argparse.ArgumentTypeError: If the value is not a number in range.

    """
    seconds = NonNegativeFloat.type_parser(arg)
    if not math.isfinite(seconds) or seconds > _MAX_HOLD_SECONDS:
        msg = f"invalid value: '{arg}' is not a number from 0 to {_MAX_HOLD_SECONDS:g}."
        raise argparse.ArgumentTypeError(msg)
    return seconds


def _build_global_parser(*, add_help: bool = True) -> argparse.ArgumentParser:
    """Build global options independently of effect discovery."""
    parser = argparse.ArgumentParser(
        prog="tte",
        add_help=add_help,
        description="A terminal visual effects engine, application, and library",
        epilog="Ex: ls -a | tte decrypt --typing-speed 2 --ciphertext-colors 008000 00cb00 00ff00 "
        "--final-gradient-stops eda000 --final-gradient-steps 12 --final-gradient-direction vertical",
    )

    parser.add_argument("--input-file", "-i", type=str, help="File to read input from")
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version="TerminalTextEffects " + _get_version(),
    )
    parser.add_argument(
        "--print-completion",
        nargs="?",
        const="",
        type=parse_completion_shell,
        metavar="{bash,zsh,powershell}",
        help="Print completion setup commands, or a completion script for the requested shell, and exit.",
    )
    parser.add_argument(
        "--tui",
        action="store_true",
        help=(
            "Open the interactive interface with the input text, if any, loaded for editing. Running tte with no "
            "effect and no input, or with input and no effect, also opens it when the interface is installed "
            "(pip install 'terminaltexteffects[tui]')."
        ),
    )
    parser.add_argument(
        "--random-effect",
        "-R",
        action="store_true",
        help="Randomly select an effect to apply; with --repeat, select again for each playback.",
    )
    parser.add_argument(
        "--repeat",
        type=NonNegativeInt.type_parser,
        default=1,
        metavar="COUNT",
        help=(
            "Play an effect COUNT times; with --random-effect, select anew each time "
            "(0 repeats until interrupted; default: 1)."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed to use for random effect selection",
    )
    random_include_exclude_group = parser.add_mutually_exclusive_group()
    random_include_exclude_group.add_argument(
        "--include-effects",
        type=str,
        nargs="+",
        help="Space-separated list of Effects to include when randomly selecting an effect",
    )
    random_include_exclude_group.add_argument(
        "--exclude-effects",
        type=str,
        nargs="+",
        help="Space-separated list of Effects to exclude when randomly selecting an effect",
    )

    recording_group = parser.add_argument_group("Recording and playback")
    record_play_group = recording_group.add_mutually_exclusive_group()
    record_play_group.add_argument(
        "--export",
        type=Path,
        metavar="FILE",
        help=(
            f"Render the effect without displaying it and save the frames to FILE. A {RECORDING_SUFFIX} file (or any "
            "other extension) plays back with --play; a .gif or .webp file is an animation of the canvas, which "
            f"needs Pillow ({export.INSTALL_HINT}). Requires --frame-rate greater than 0, which becomes the playback "
            "rate."
        ),
    )
    record_play_group.add_argument(
        "--play",
        type=Path,
        metavar="PATH",
        help=(
            f"Play a recording file, or every {RECORDING_SUFFIX} file in a directory in filename order, without "
            "running the effects. No effect or input is required."
        ),
    )
    recording_group.add_argument(
        "--hold",
        type=_hold_seconds,
        default=0.0,
        metavar="SECONDS",
        help=(
            f"Hold the final frame of each effect playback or recording for SECONDS (0 to {_MAX_HOLD_SECONDS:g}) "
            "before continuing or exiting (default: 0)."
        ),
    )
    recording_group.add_argument(
        "--shuffle",
        action="store_true",
        help="With --play on a directory, play recordings in random order (reproducible with --seed).",
    )
    recording_group.add_argument(
        "--alt-screen",
        action="store_true",
        help=(
            "Display output in the terminal's alternate screen and restore the original screen when it ends. "
            "The final frame is not left in the terminal; combine with --hold to keep it visible first."
        ),
    )

    # Future: add a CLI argument for a default text color so dynamic color-handling effects can use
    # it when input characters have no parsed colors.
    TerminalConfig._populate_parser(parser)

    return parser


def build_parser(
    *,
    include_user_effects: bool = True,
    skip_broken_effects: bool = False,
) -> tuple[argparse.ArgumentParser, dict[str, tuple[type[BaseEffect], type[BaseConfig]]]]:
    """Build the CLI parser and discover available effects.

    This registers built-in effect modules and, when requested, user-provided
    effect modules from the XDG config effects directory and `TTE_DEV_EFFECTS_DIR`. It returns the parsed
    CLI parser together with a mapping of effect command names to their effect
    and config classes.

    A user effect module in the XDG config effects directory that fails to import or register is
    skipped with a warning on standard error. Failures in built-in and development effect modules
    are raised, unless `skip_broken_effects` is set.

    Args:
        include_user_effects: Whether to load external effects, including opted-in development effects.
        skip_broken_effects: Whether to leave out built-in and development effect modules that fail to import or
            register instead of raising. The interactive interface lists them and reports why. Built-in modules that
            `terminaltexteffects.effects` imports itself still raise when the package is imported.

    Returns:
        tuple[argparse.ArgumentParser, dict[str, tuple[type[BaseEffect], type[BaseConfig]]]]: The CLI parser and a
            mapping of effect names to their classes and configurations.

    Raises:
        ValueError: If built-in or development effect modules register the same effect command.

    """
    parser = _build_global_parser()

    subparsers = parser.add_subparsers(
        title="Effect",
        description="Name of the effect to apply. Use <effect> -h for effect specific help.",
        help="Available Effects",
        required=False,
        dest="effect",
    )

    effect_resource_map: dict[str, tuple[type[BaseEffect], type[BaseConfig]]] = {}

    def _register_effect_from_module(module: ModuleType) -> None:
        """Register an effect module's resources and populate its CLI options.

        If the module defines `get_effect_resources()`, that callable is expected to
        return the effect command name, effect class, and config class. The config class
        is then used to populate the subparser for that effect command.

        Args:
            module: The module to inspect for effect resources.

        Raises:
            ValueError: If the module registers an effect command that has already been
                registered.

        """
        if hasattr(module, "get_effect_resources"):
            effect_cmd: str
            effect_class: type[BaseEffect]
            config_class: type[BaseConfig]
            effect_cmd, effect_class, config_class = module.get_effect_resources()
            if effect_cmd in effect_resource_map:
                msg = f"Duplicate effect command detected: {effect_cmd}"
                raise ValueError(msg)
            effect_resource_map[effect_cmd] = (effect_class, config_class)
            config_class._populate_parser(subparsers)

    _EFFECT_FILES.clear()

    def _register_file(plugin_file: Path, register: Callable[[], object], *, skip_broken: bool) -> None:
        """Run `register` for the module in `plugin_file`, and note the file of each command it registers.

        With `skip_broken`, a module that fails to import or register is left out instead of raising.
        """
        before = set(effect_resource_map)
        try:
            register()
        except (Exception, SystemExit):
            if not skip_broken:
                raise
            # The interface lists the module and shows why it is left out.
            for effect_cmd in set(effect_resource_map) - before:
                del effect_resource_map[effect_cmd]
            return
        for effect_cmd in set(effect_resource_map) - before:
            _EFFECT_FILES[effect_cmd] = plugin_file.resolve()

    for module_info in pkgutil.iter_modules(
        terminaltexteffects.effects.__path__,
        terminaltexteffects.effects.__name__ + ".",
    ):
        if not include_user_effects and module_info.name == "terminaltexteffects.effects.effect_dev":
            continue
        spec = importlib.util.find_spec(module_info.name)
        origin = Path(spec.origin) if spec is not None and spec.origin else Path(module_info.name)
        _register_file(
            origin,
            lambda name=module_info.name: _register_effect_from_module(importlib.import_module(name)),
            skip_broken=skip_broken_effects,
        )

    if include_user_effects:
        for plugin_file, module_name in _external_effect_files(_user_effects_dir()):
            _register_file(
                plugin_file,
                lambda plugin_file=plugin_file, module_name=module_name: _register_user_effect(
                    plugin_file, module_name, subparsers, effect_resource_map
                ),
                skip_broken=False,
            )
        development_dir = os.environ.get("TTE_DEV_EFFECTS_DIR")
        if development_dir is not None:
            directory = Path(development_dir).expanduser().resolve()
            if not development_dir or not directory.is_dir():
                msg = f"TTE_DEV_EFFECTS_DIR must name an existing directory: {development_dir!r}"
                raise ValueError(msg)
            for plugin_file, module_name in _external_effect_files(directory, _DEV_EFFECT_MODULE_PREFIX):
                _register_file(
                    plugin_file,
                    lambda plugin_file=plugin_file, module_name=module_name: _register_effect_from_module(
                        _load_external_module(plugin_file, module_name)
                    ),
                    skip_broken=skip_broken_effects,
                )

    return parser, effect_resource_map


def build_parsers_and_parse_args() -> tuple[argparse.Namespace, dict[str, tuple[type[BaseEffect], type[BaseConfig]]]]:
    """Build the CLI parser, discover available effects, and parse arguments."""
    preliminary = _build_global_parser(add_help=False)
    preliminary.add_argument("effect_arguments", nargs=argparse.REMAINDER)
    global_args, _ = preliminary.parse_known_args()
    include_user_effects = global_args.print_completion is None
    # The interface lists broken effects itself, so they must not stop it from opening.
    tui_may_open = global_args.tui or (
        not global_args.effect_arguments
        and not global_args.random_effect
        and global_args.export is None
        and global_args.play is None
    )
    parser, effect_resource_map = build_parser(
        include_user_effects=include_user_effects,
        skip_broken_effects=tui_may_open,
    )
    return parser.parse_args(), effect_resource_map


def _get_version() -> str:
    """Return the installed package version or a local-development fallback."""
    try:
        return version("terminaltexteffects")
    except PackageNotFoundError:
        project_file = Path(__file__).resolve().parents[1] / "pyproject.toml"
        for line in project_file.read_text(encoding="utf-8").splitlines():
            if line.startswith('version = "'):
                return line.removeprefix('version = "').removesuffix('"')
        return "unknown"


def _create_effect(
    effect_name: str,
    input_data: str,
    effect_resource_map: dict[str, tuple[type[BaseEffect], type[BaseConfig]]],
    terminal_config: TerminalConfig,
    effect_args: argparse.Namespace | None,
) -> BaseEffect:
    """Create an effect with the requested configuration or its defaults."""
    effect_class, effect_config_class = effect_resource_map[effect_name]
    effect_config = effect_config_class._build_config(effect_args)
    return effect_class(input_data, effect_config, terminal_config)


def _create_random_playback(
    available_effects: list[str],
    effect_resource_map: dict[str, tuple[type[BaseEffect], type[BaseConfig]]],
    input_data: str,
    terminal_config: TerminalConfig,
    terminal: Terminal,
) -> tuple[BaseEffect, Iterator[str]]:
    """Choose and create one fresh random effect using the prepared output geometry."""
    effect_name = random.choice(available_effects)
    effect = _create_effect(effect_name, input_data, effect_resource_map, terminal_config, None)
    effect._terminal_dimensions_override = (terminal._terminal_width, terminal._terminal_height)
    return effect, iter(effect)


def _get_available_effects(
    args: argparse.Namespace,
    effect_resource_map: dict[str, tuple[type[BaseEffect], type[BaseConfig]]],
) -> list[str]:
    """Return effect names allowed by the random-selection filters."""
    if args.include_effects:
        return [effect for effect in effect_resource_map if effect in args.include_effects]
    if args.exclude_effects:
        return [effect for effect in effect_resource_map if effect not in args.exclude_effects]
    return list(effect_resource_map)


@contextmanager
def _alternate_screen(*, enabled: bool) -> Generator[None, None, None]:
    """Show output in the terminal's alternate screen when `enabled`, restoring the original screen afterward.

    Text attributes are reset before leaving, including when the block raises or is interrupted.
    """
    if not enabled:
        yield
        return
    sys.stdout.write(ansitools.enter_alternate_screen())
    try:
        yield
    finally:
        sys.stdout.write(ansitools.reset_all() + ansitools.exit_alternate_screen())
        sys.stdout.flush()


def _print_replays(
    effect: BaseEffect,
    iterator: Iterator[str],
    terminal: Terminal,
    count: int,
    next_playback_factory: Callable[[], tuple[BaseEffect, Iterator[str]]] | None = None,
    hold: float = 0.0,
) -> None:
    """Print fresh playbacks, stopping on empty output or after `count` runs.

    A zero `count` repeats until interrupted. The first iterator is constructed
    before opening terminal output so input validation remains fail-fast. When
    `next_playback_factory` is provided, it creates a newly selected effect and
    iterator for each completed playback. A nonzero `hold` keeps the final frame of
    each playback that rendered frames on screen for `hold` seconds, including the last.
    """
    completed = 0
    while True:
        rendered = False
        for frame in iterator:
            terminal.print(frame)
            rendered = True
        completed += 1
        if not rendered:
            return
        if hold:
            time.sleep(hold)
        if count and completed >= count:
            return
        if next_playback_factory is None:
            iterator = iter(effect)
        else:
            effect, iterator = next_playback_factory()


def _record_playbacks(
    path: Path,
    effect_name: str,
    effect: BaseEffect,
    count: int,
    next_playback_factory: Callable[[tuple[int, int]], tuple[str, BaseEffect]] | None = None,
    on_frame: Callable[[int], None] | None = None,
) -> tuple[RecordingHeader, int, int]:
    """Render `count` playbacks with a frame clock and write them to a recording.

    Every playback uses the canvas geometry resolved for the first one. When
    `next_playback_factory` is provided, it creates a newly selected effect for each
    playback after the first. Empty output ends the recording early, as it does for
    live repeats. `on_frame`, when provided, is called with the frame count after each
    frame is written.

    Returns:
        tuple[RecordingHeader, int, int]: The recording header, frame count, and segment count.

    """
    effect._frame_clock = True
    iterator = iter(effect)
    terminal = iterator.terminal
    header = RecordingHeader(
        tte_version=_get_version(),
        width=terminal.visible_right,
        height=terminal.visible_top,
        frame_rate=terminal.config.frame_rate,
    )
    terminal_dimensions = (terminal._terminal_width, terminal._terminal_height)
    effect._terminal_dimensions_override = terminal_dimensions
    segments = 0
    with RecordingWriter(path, header) as writer:
        while True:
            writer.begin_segment(effect_name)
            segments += 1
            rendered = False
            for frame in iterator:
                writer.write_frame(frame)
                rendered = True
                if on_frame is not None:
                    on_frame(writer.frame_count)
            if not rendered or segments >= count:
                break
            if next_playback_factory is not None:
                effect_name, effect = next_playback_factory(terminal_dimensions)
            iterator = iter(effect)
        frame_count = writer.frame_count
    return header, frame_count, segments


def _create_random_recording(
    available_effects: list[str],
    effect_resource_map: dict[str, tuple[type[BaseEffect], type[BaseConfig]]],
    input_data: str,
    terminal_config: TerminalConfig,
    terminal_dimensions: tuple[int, int],
) -> tuple[str, BaseEffect]:
    """Choose and create one fresh random effect for recording with the recorded geometry."""
    effect_name = random.choice(available_effects)
    effect = _create_effect(effect_name, input_data, effect_resource_map, terminal_config, None)
    effect._frame_clock = True
    effect._terminal_dimensions_override = terminal_dimensions
    return effect_name, effect


def _find_recordings(path: Path) -> list[Path]:
    """Return the recording at `path`, or the top-level recordings in a directory sorted by filename.

    Raises:
        RecordingError: If `path` does not exist, a directory cannot be read, or it contains no recordings.

    """
    if path.is_dir():
        try:
            recordings = sorted(
                (child for child in path.iterdir() if child.suffix == RECORDING_SUFFIX and child.is_file()),
                key=lambda child: child.name,
            )
        except OSError as error:
            msg = f"Cannot read recording directory {str(path)!r}: {error.strerror or error}."
            raise RecordingError(msg) from error
        if not recordings:
            msg = f"No {RECORDING_SUFFIX} recordings found in directory: {str(path)!r}."
            raise RecordingError(msg)
        return recordings
    if not path.is_file():
        msg = f"Recording not found: {str(path)!r}."
        raise RecordingError(msg)
    return [path]


# Recordings up to this size are held in memory, verified by digest, and replayed without per-frame checks.
# Larger recordings are only header-checked on later passes; every frame is validated again as it streams, so a
# replacement with another valid recording plays, and late corruption can show earlier frames before failing.
_MAX_VERIFIED_RECORDING_BYTES = 256 * 1024 * 1024


@dataclass(frozen=True)
class _ValidatedRecording:
    """A recording that passed complete validation before playback.

    Attributes:
        header (RecordingHeader): The recording header.
        digest (bytes | None): SHA-256 digest of the validated file, or `None` when the file is too large to hold
            in memory and must be validated again on every pass.

    """

    header: RecordingHeader
    digest: bytes | None


def _validate_recordings(paths: list[Path]) -> dict[Path, _ValidatedRecording]:
    """Read every recording completely so invalid files fail before playback starts.

    Raises:
        RecordingError: If any recording is invalid; the message names the file.

    """
    return {path: _validate_recording(path) for path in paths}


def _validate_recording(path: Path) -> _ValidatedRecording:
    """Read and validate one recording completely.

    Raises:
        RecordingError: If the recording is invalid; the message names the file.

    """
    try:
        data = _read_verifiable_recording(path)
        with RecordingReader(path, data) as reader:
            reader.validate()
            return _ValidatedRecording(reader.header, None if data is None else hashlib.sha256(data).digest())
    except RecordingError as error:
        msg = f"{path}: {error.message}"
        raise RecordingError(msg) from error


def _read_verifiable_recording(path: Path) -> bytes | None:
    """Return the bytes of a recording small enough to verify by digest, or `None` for a larger one.

    Raises:
        RecordingError: If the file cannot be read.

    """
    try:
        if path.stat().st_size > _MAX_VERIFIED_RECORDING_BYTES:
            return None
        return path.read_bytes()
    except OSError as error:
        msg = f"Cannot read recording {str(path)!r}: {error.strerror or error}."
        raise RecordingError(msg) from error


def _open_validated_recording(path: Path, recording: _ValidatedRecording) -> tuple[RecordingReader, bool]:
    """Open a validated recording for playback.

    A recording verified by digest is replayed from the exact bytes that were validated, so its frames need no
    further checks. A larger recording is read from disk, and its frames are validated again as they play.

    Returns:
        tuple[RecordingReader, bool]: The reader, and whether its frames must be validated during playback.

    Raises:
        RecordingError: If the recording cannot be read or changed after validation; the message names the file.

    """
    changed = RecordingError(f"{path}: Recording changed after validation.")
    if recording.digest is not None:
        data = _read_verifiable_recording(path)
        if data is None or hashlib.sha256(data).digest() != recording.digest:
            raise changed
        return RecordingReader(path, data), False
    try:
        reader = RecordingReader(path)
    except RecordingError as error:
        msg = f"{path}: {error.message}"
        raise RecordingError(msg) from error
    if reader.header != recording.header:
        reader.close()
        raise changed
    return reader, True


def _anchor_offsets(anchor: str, spare_columns: int, spare_rows: int) -> tuple[int, int]:
    """Return column and row offsets, counted from the left and bottom, that place content at `anchor`.

    This mirrors the canvas anchoring used for live output.
    """
    column_offset = row_offset = 0
    if anchor in ("s", "n", "c"):
        column_offset = spare_columns // 2
    elif anchor in ("se", "e", "ne"):
        column_offset = spare_columns
    if anchor in ("w", "e", "c"):
        row_offset = spare_rows // 2
    elif anchor in ("nw", "n", "ne"):
        row_offset = spare_rows
    return column_offset, row_offset


class _FrameLayout:
    """Place recorded frames on the prepared playback canvas."""

    def __init__(self, header: RecordingHeader, terminal: Terminal, canvas_size: tuple[int, int]) -> None:
        canvas_width, canvas_height = canvas_size
        inner_column, inner_row = _anchor_offsets(
            terminal.config.anchor_canvas,
            canvas_width - header.width,
            canvas_height - header.height,
        )
        column_offset = terminal.canvas_column_offset + inner_column
        bottom_rows = terminal.canvas_row_offset + inner_row
        self._identity = column_offset == 0 and bottom_rows == 0 and terminal.visible_top == header.height
        self._identity = self._identity and terminal.visible_right == header.width
        self._prefix = " " * column_offset
        self._suffix = " " * (terminal.visible_right - column_offset - header.width)
        blank_row = " " * terminal.visible_right
        self._top_rows = [blank_row] * (terminal.visible_top - bottom_rows - header.height)
        self._bottom_rows = [blank_row] * bottom_rows

    def place(self, frame: str) -> str:
        """Return `frame` padded to the playback canvas."""
        if self._identity:
            return frame
        rows = [self._prefix + row + self._suffix for row in frame.split("\n")]
        return "\n".join(self._top_rows + rows + self._bottom_rows)


class _FramePacer:
    """Pace frames on a fixed monotonic schedule."""

    def __init__(self, frame_rate: int) -> None:
        self._period = 1 / frame_rate if frame_rate else 0.0
        self._next_frame_time: float | None = None

    def wait(self) -> None:
        """Sleep until the next frame is due.

        The schedule restarts when playback falls more than a frame behind, so a
        stall is not followed by a burst of unpaced frames.
        """
        if not self._period:
            return
        now = time.monotonic()
        if self._next_frame_time is None or now - self._next_frame_time > self._period:
            self._next_frame_time = now
        elif self._next_frame_time > now:
            time.sleep(self._next_frame_time - now)
        self._next_frame_time += self._period


# Global options rejected with `--play`: canvas, text, input, and color handling are fixed when a recording is
# made, and effect-selection filters apply only to running effects.
_PLAYBACK_REJECTED_OPTIONS = (
    "canvas_width",
    "canvas_height",
    "anchor_text",
    "xterm_colors",
    "no_color",
    "terminal_background_color",
    "existing_color_handling",
    "tab_width",
    "wrap_text",
    "ignore_terminal_dimensions",
    "include_effects",
    "exclude_effects",
)


def _options_given(argv: list[str]) -> dict[str, str]:
    """Return the global options present on the command line, mapping each destination to its option name.

    Every default is suppressed, so only options actually given appear, including abbreviated and
    `--option=value` forms and options given their default value.
    """
    probe = _build_global_parser(add_help=False)
    option_names: dict[str, str] = {}
    for action in probe._actions:
        action.default = argparse.SUPPRESS
        if action.option_strings:
            option_names[action.dest] = max(action.option_strings, key=len)
    probe.add_argument("effect_arguments", nargs=argparse.REMAINDER)
    known_args, _ = probe.parse_known_args(argv)
    return {dest: option_names[dest] for dest in vars(known_args) if dest in option_names}


def _join_names(names: list[str]) -> str:
    """Join names as an English list, such as `a, b, and c`."""
    if len(names) <= 2:
        return " and ".join(names)
    return f"{', '.join(names[:-1])}, and {names[-1]}"


def _play_recordings(args: argparse.Namespace, frame_rate_override: int | None) -> None:
    """Validate and play the recordings selected by `--play`.

    Raises:
        RecordingError: If a recording is invalid or the terminal is smaller than the recorded canvas.

    """
    paths = _find_recordings(args.play)
    recordings = _validate_recordings(paths)
    canvas_size = (
        max(recording.header.width for recording in recordings.values()),
        max(recording.header.height for recording in recordings.values()),
    )
    terminal_width, terminal_height = shutil.get_terminal_size()
    if canvas_size[0] > terminal_width or canvas_size[1] > terminal_height:
        msg = (
            f"Recording canvas is {canvas_size[0]}x{canvas_size[1]} but the terminal is "
            f"{terminal_width}x{terminal_height}. Enlarge the terminal to play it."
        )
        raise RecordingError(msg)
    terminal_config = TerminalConfig._build_config(args)
    terminal_config.canvas_width, terminal_config.canvas_height = canvas_size
    terminal_config.ignore_terminal_dimensions = False
    terminal_config.wrap_text = False
    terminal_config.frame_rate = 0
    terminal = Terminal("", terminal_config, terminal_dimensions=(terminal_width, terminal_height))
    layouts = {path: _FrameLayout(recording.header, terminal, canvas_size) for path, recording in recordings.items()}

    with _alternate_screen(enabled=args.alt_screen):
        try:
            terminal.prep_canvas()
            completed = 0
            while True:
                order = list(paths)
                if args.shuffle:
                    random.shuffle(order)
                pass_rendered = False
                for path in order:
                    rendered = _play_recording(path, recordings[path], layouts[path], terminal, frame_rate_override)
                    pass_rendered = pass_rendered or rendered
                    if rendered and args.hold:
                        time.sleep(args.hold)
                completed += 1
                # A pass without frames would otherwise repeat at full speed, unlike live replay.
                if not pass_rendered or (args.repeat and completed >= args.repeat):
                    return
        finally:
            # Recorded frames are untrusted; never leave their text attributes active in the shell. Leaving the
            # alternate screen resets them as well.
            if not args.alt_screen:
                sys.stdout.write(ansitools.reset_all())
            terminal.restore_cursor("" if args.alt_screen else "\n")


def _play_recording(
    path: Path,
    recording: _ValidatedRecording,
    layout: _FrameLayout,
    terminal: Terminal,
    frame_rate_override: int | None,
) -> bool:
    """Play one validated recording on the prepared terminal.

    Returns:
        bool: Whether the recording rendered any frames.

    Raises:
        RecordingError: If the recording changed after validation or is invalid; the message names the file.

    """
    reader, validate_frames = _open_validated_recording(path, recording)
    rendered = False
    with reader:
        pacer = _FramePacer(reader.header.frame_rate if frame_rate_override is None else frame_rate_override)
        try:
            for frame in reader.frames(validate_frames=validate_frames):
                pacer.wait()
                terminal.print(layout.place(frame))
                rendered = True
        except RecordingError as error:
            msg = f"{path}: {error.message}"
            raise RecordingError(msg) from error
    return rendered


def _exit_with_error(message: str) -> NoReturn:
    """Print an error message to standard error and exit with status `1`."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def _run_playback(args: argparse.Namespace) -> None:
    """Run `--play`, exiting with status `1` on invalid options, recordings, or interruption."""
    if args.effect or args.random_effect or args.input_file:
        _exit_with_error("--play cannot be combined with an effect, --random-effect, or --input-file.")
    given = _options_given(sys.argv[1:])
    rejected = [given[dest] for dest in _PLAYBACK_REJECTED_OPTIONS if dest in given]
    if rejected:
        _exit_with_error(
            f"{_join_names(rejected)} cannot be used with --play; canvas, text, color, and effect-selection "
            "options are fixed when a recording is made."
        )
    frame_rate_override = cast("int", args.frame_rate) if "frame_rate" in given else None
    try:
        _play_recordings(args, frame_rate_override)
    except RecordingError as error:
        _exit_with_error(error.message)
    except KeyboardInterrupt:
        sys.exit(1)


def _check_recording_options(args: argparse.Namespace) -> None:
    """Exit with status `1` when playback-only or recording options are used incorrectly."""
    if args.shuffle:
        _exit_with_error("--shuffle requires --play.")
    if args.export is not None:
        given = _options_given(sys.argv[1:])
        display_options = [given[dest] for dest in ("hold", "alt_screen") if dest in given]
        if display_options:
            _exit_with_error(
                f"{_join_names(display_options)} cannot be combined with --export, which displays nothing."
            )
        if args.repeat == 0:
            _exit_with_error("--export cannot be combined with --repeat 0.")
        if args.frame_rate == 0:
            _exit_with_error("--export requires --frame-rate greater than 0.")


_PROGRESS_INTERVAL = 0.1
"""Seconds between updates of the frame count shown while `--export` renders or exports to a terminal."""


class _RecordingProgress:
    """Report `--export` progress on standard error.

    On a terminal, the frame count updates in place while frames render, draw, and encode. Otherwise only whole
    lines are printed.
    """

    def __init__(self) -> None:
        self._live = _is_terminal(sys.stderr)
        self._last_update = 0.0
        self._shown = False

    def frame(self, count: int) -> None:
        """Show `count` frames rendered, at most every `_PROGRESS_INTERVAL` seconds, on a terminal."""
        self._update(f"Rendering frame {count}")

    def export_step(self, step: str, count: int, total: int) -> None:
        """Show `count` of `total` frames done in export `step`, at most every `_PROGRESS_INTERVAL` seconds."""
        self._update(f"{step} frame {count} of {total}", final=count == total)

    def _update(self, message: str, *, final: bool = False) -> None:
        if not self._live:
            return
        now = time.monotonic()
        if now - self._last_update < _PROGRESS_INTERVAL and not final:
            return
        self._last_update = now
        sys.stderr.write(f"\r\x1b[K{message}")
        sys.stderr.flush()
        self._shown = True

    def line(self, message: str) -> None:
        """Replace any frame count with `message` on its own line."""
        self.clear()
        print(message, file=sys.stderr, flush=True)

    def clear(self) -> None:
        """Erase the frame count, if one is shown."""
        if self._shown:
            sys.stderr.write("\r\x1b[K")
            sys.stderr.flush()
            self._shown = False


def _run_recording(
    args: argparse.Namespace,
    effect_name: str,
    effect: BaseEffect,
    available_effects: list[str] | None,
    effect_resource_map: dict[str, tuple[type[BaseEffect], type[BaseConfig]]],
    input_data: str,
) -> None:
    """Run `--export` and report the result, exiting with status `1` on failure or interruption."""
    next_recording_factory: Callable[[tuple[int, int]], tuple[str, BaseEffect]] | None = None
    if available_effects is not None:
        next_recording_factory = partial(
            _create_random_recording,
            available_effects,
            effect_resource_map,
            input_data,
            effect.terminal_config,
        )
    fmt = export.format_for(args.export)
    progress = _RecordingProgress()
    record = partial(
        _record_playbacks,
        effect_name=effect_name,
        effect=effect,
        count=args.repeat,
        next_playback_factory=next_recording_factory,
        on_frame=progress.frame,
    )
    missing: frozenset[str] = frozenset()
    try:
        try:
            if fmt is export.FORMATS[0]:
                header, frame_count, segments = record(args.export)
            else:
                with tempfile.TemporaryDirectory(prefix="tte-record-") as folder:
                    recording = Path(folder) / f"effect{RECORDING_SUFFIX}"
                    header, frame_count, segments = record(recording)
                    progress.line(f"Drawing {frame_count} frames to {fmt.name}")
                    missing = export.export_recording(
                        recording,
                        args.export,
                        fmt,
                        fps=header.frame_rate,
                        on_progress=lambda step, count, total: progress.export_step(step, count, total or frame_count),
                    )
        finally:
            progress.clear()
    except (EmptyInputError, UnsupportedAnsiSequenceError, RecordingError, export.ExportError) as e:
        _exit_with_error(str(e))
    except OSError as e:
        _exit_with_error(f"Cannot write recording {str(args.export)!r}: {e.strerror or e}.")
    except KeyboardInterrupt:
        sys.exit(1)
    if missing:
        symbols = " ".join(sorted(missing))
        print(f"No installed font has these symbols, drawn as boxes: {symbols}", file=sys.stderr)
    print(
        f"Recorded {frame_count} frames in {segments} segment{'s' if segments != 1 else ''} "
        f"({header.width}x{header.height} at {header.frame_rate} fps) to {args.export}",
        file=sys.stderr,
    )


def _read_input(args: argparse.Namespace) -> str:
    """Return text from `--input-file` or piped standard input, exiting with status `1` if the file cannot be read."""
    if not args.input_file:
        return Terminal.get_piped_input()
    try:
        return Path(args.input_file).read_text(encoding="UTF-8")
    except FileNotFoundError:
        print(f"File not found: {args.input_file}")
        sys.exit(1)
    except Exception as e:  # noqa: BLE001
        print(f"Error reading file: {args.input_file} - {e}")
        sys.exit(1)


def _is_terminal(stream: object) -> bool:
    """Return whether `stream` is attached to a terminal."""
    isatty = getattr(stream, "isatty", None)
    try:
        return bool(isatty()) if callable(isatty) else False
    except (OSError, ValueError):
        return False


def _run_tui(
    args: argparse.Namespace,
    effect_resource_map: dict[str, tuple[type[BaseEffect], type[BaseConfig]]],
    input_data: str,
) -> None:
    """Open the interactive interface, exiting with status `1` if it is not installed or has no terminal."""
    if not tui.is_available():
        _exit_with_error(tui.INSTALL_HINT)
    if not _is_terminal(sys.stdout):
        _exit_with_error("--tui needs standard output to be a terminal.")
    # The interface watches every effect directory, and imports a module again when its file changes.
    effect_dirs = [
        (Path(path).resolve(), terminaltexteffects.effects.__name__ + ".")
        for path in terminaltexteffects.effects.__path__
    ]
    # User effects keep their bare module names, so `import name` in a module finds the reloaded module.
    effect_dirs.append((_user_effects_dir(), ""))
    development_dir = os.environ.get("TTE_DEV_EFFECTS_DIR")
    if development_dir:
        effect_dirs.append((Path(development_dir).expanduser().resolve(), _DEV_EFFECT_MODULE_PREFIX))
    try:
        tui.run(
            effect_resource_map,
            input_data,
            args.input_file,
            args.effect,
            effect_dirs,
            dict(_EFFECT_FILES),
            _check_user_module_name,
        )
    except OSError as e:
        _exit_with_error(f"Cannot open the terminal for keyboard input: {e}")


def _can_open_tui() -> bool:
    """Return whether the interface can open without being requested explicitly."""
    return tui.is_available() and _is_terminal(sys.stdout)


def _input_or_tui(
    args: argparse.Namespace,
    effect_resource_map: dict[str, tuple[type[BaseEffect], type[BaseConfig]]],
) -> str | None:
    """Return the input text to play, or `None` when the interface opened or there is nothing to play.

    The interface opens for `--tui`, and for runs without an effect when it is installed and standard output is a
    terminal. A run without an effect or input that cannot open the interface prints a usage hint.
    """
    if args.tui:
        _run_tui(args, effect_resource_map, _read_input(args))
        return None
    _check_recording_options(args)
    no_effect = not args.effect and not args.random_effect and args.export is None
    if no_effect and not args.input_file and _is_terminal(sys.stdin):
        if _can_open_tui():
            _run_tui(args, effect_resource_map, "")
            return None
        print("usage: tte [options] <effect> [effect options], with input piped in or read by -i FILE", file=sys.stderr)
        print("Run tte -h for help.", file=sys.stderr)
        if not tui.is_available():
            print(tui.INSTALL_HINT, file=sys.stderr)
        return None
    input_data = _read_input(args)
    if not input_data.strip():
        return None
    if no_effect and _can_open_tui():
        _run_tui(args, effect_resource_map, input_data)
        return None
    return input_data


def main() -> None:
    """Run the terminaltexteffects command line interface.

    Parse CLI arguments, load input text, choose and configure the requested effect,
    and stream rendered frames to the terminal. Empty or whitespace-only input is
    a successful no-op. The process exits with status `1` for invalid effect
    selection, input file read failures, or keyboard interruption.

    With `--tui`, or with no effect selected when the interface is installed and standard
    output is a terminal, the interactive interface opens instead, with any input loaded.
    """
    args, effect_resource_map = build_parsers_and_parse_args()
    if args.print_completion is not None:
        output = (
            get_completion_script(args.print_completion) if args.print_completion else get_completion_instructions()
        )
        print(output, end="")
        return
    if args.seed is not None:
        random.seed(args.seed)
    if args.play is not None:
        _run_playback(args)
        return
    input_data = _input_or_tui(args, effect_resource_map)
    if input_data is None:
        return

    available_effects: list[str] | None = None
    selected_effect_name = args.effect
    if args.random_effect:
        available_effects = _get_available_effects(args, effect_resource_map)
        if not available_effects:
            print("Error: No effects available for random selection based on include/exclude filters.\n")
            sys.exit(1)

        selected_effect_name = random.choice(available_effects)
    elif not args.effect:
        print("Error: No effect specified. Must specify an effect or use --random-effect.\n")
        if not tui.is_available():
            print(tui.INSTALL_HINT + " to edit and preview effects interactively.\n")
        sys.exit(1)

    terminal_config = TerminalConfig._build_config(args)
    if args.export is not None:
        # Fail before rendering when GIF or WebP conversion is impossible, but after empty input has returned.
        problem = export.format_problem(export.format_for(args.export))
        if problem is not None:
            _exit_with_error(problem)
        # Record the canvas alone; playback anchors it within the terminal.
        terminal_config.ignore_terminal_dimensions = True

    assert selected_effect_name is not None
    effect = _create_effect(
        selected_effect_name,
        input_data,
        effect_resource_map,
        terminal_config,
        None if args.random_effect else args,
    )
    if args.export is not None:
        _run_recording(args, selected_effect_name, effect, available_effects, effect_resource_map, input_data)
        return
    try:
        effect_iterator = iter(effect)
        end_symbol = "" if args.alt_screen else "\n"
        with _alternate_screen(enabled=args.alt_screen), effect.terminal_output(end_symbol) as terminal:
            next_playback_factory: Callable[[], tuple[BaseEffect, Iterator[str]]] | None = None
            if available_effects is not None:
                next_playback_factory = partial(
                    _create_random_playback,
                    available_effects,
                    effect_resource_map,
                    input_data,
                    terminal_config,
                    terminal,
                )
            _print_replays(effect, effect_iterator, terminal, args.repeat, next_playback_factory, hold=args.hold)
    except (EmptyInputError, UnsupportedAnsiSequenceError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == "__main__":
    main()
