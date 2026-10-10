"""Package entry point for the TerminalTextEffects command line interface."""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import os
import pkgutil
import random
import sys
from functools import partial
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import TYPE_CHECKING, cast

import terminaltexteffects.effects
from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.utils.argutils import NonNegativeInt
from terminaltexteffects.utils.exceptions import EmptyInputError, UnsupportedAnsiSequenceError
from terminaltexteffects.utils.shell_completion import (
    get_completion_instructions,
    get_completion_script,
    parse_completion_shell,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from importlib.machinery import SourceFileLoader
    from types import ModuleType

    from terminaltexteffects.engine.base_config import BaseConfig
    from terminaltexteffects.engine.base_effect import BaseEffect


_USER_EFFECT_MODULE_PREFIX = "_tte_user_"
_DEV_EFFECT_MODULE_PREFIX = "_tte_dev_"


def _external_effect_files(directory: Path, prefix: str) -> Iterator[tuple[Path, str]]:
    """Yield flat external module paths and their prefixed module names in deterministic order."""
    for plugin_file in sorted(directory.glob("*.py")):
        if plugin_file.name == "__init__.py":
            continue
        yield plugin_file, prefix + plugin_file.stem


def _load_external_module(plugin_file: Path, module_name: str) -> ModuleType:
    """Load a flat external module without altering the import path.

    Raises:
        ImportError: If no module specification can be created for `plugin_file`.

    """
    spec = importlib.util.spec_from_file_location(module_name, plugin_file)
    if spec is None or spec.loader is None:
        msg = f"Unable to create a module specification for {plugin_file}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    # Dataclasses and other import-time machinery look the module up in `sys.modules`.
    sys.modules[module_name] = module
    try:
        # Flat .py paths resolve to SourceFileLoader; typeshed also permits legacy loaders.
        cast("SourceFileLoader", spec.loader).exec_module(module)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    return module


def _validate_user_effect_resources(
    resources: object,
    effect_resource_map: dict[str, tuple[type[BaseEffect], type[BaseConfig]]],
) -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    """Validate user effect resources before any parser state is changed.

    The config class populates a disposable subparser collection, so option errors are raised
    before the real parser receives a partially populated effect command.

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
    disposable_subparsers = argparse.ArgumentParser(add_help=False).add_subparsers()
    config_class._populate_parser(disposable_subparsers)
    return effect_cmd, effect_class, config_class


def _sibling_import_name(stem: str) -> str | None:
    """Return the bare name a user module may also be imported by, or `None` if claiming it is unsafe.

    Earlier-loaded files in the custom effects directory have always been importable by their bare
    file stem. That name is only claimed when no loaded or installed module already uses it.
    """
    if not stem.isidentifier() or stem in sys.modules:
        return None
    try:
        if importlib.util.find_spec(stem) is not None:
            return None
    except (ImportError, ValueError):
        return None
    return stem


def _release_sibling_import_names() -> None:
    """Remove bare-name aliases left by an earlier discovery so rediscovery imports current files."""
    for name, module in list(sys.modules.items()):
        module_name = getattr(module, "__name__", None)
        if isinstance(module_name, str) and module_name.startswith(_USER_EFFECT_MODULE_PREFIX) and name != module_name:
            del sys.modules[name]


def _register_user_effect(
    plugin_file: Path,
    module_name: str,
    subparsers: argparse._SubParsersAction,
    effect_resource_map: dict[str, tuple[type[BaseEffect], type[BaseConfig]]],
) -> None:
    """Register one user effect plugin, or skip it with a warning if it fails to load or register."""
    sibling_name = _sibling_import_name(plugin_file.stem)
    module: ModuleType | None = None
    try:
        module = _load_external_module(plugin_file, module_name)
        if sibling_name is not None:
            sys.modules[sibling_name] = module
        if hasattr(module, "get_effect_resources"):
            effect_cmd, effect_class, config_class = _validate_user_effect_resources(
                module.get_effect_resources(),
                effect_resource_map,
            )
            config_class._populate_parser(subparsers)
            effect_resource_map[effect_cmd] = (effect_class, config_class)
    # SystemExit is a plugin failure here: a plugin calling `sys.exit()` must not end the CLI.
    except (Exception, SystemExit) as exc:  # noqa: BLE001
        sys.modules.pop(module_name, None)
        if sibling_name is not None and module is not None and sys.modules.get(sibling_name) is module:
            del sys.modules[sibling_name]
        detail = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
        print(f"Warning: Skipping user effect plugin '{plugin_file}': {detail}", file=sys.stderr)


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

    # Future: add a CLI argument for a default text color so dynamic color-handling effects can use
    # it when input characters have no parsed colors.
    TerminalConfig._populate_parser(parser)

    return parser


def build_parser(
    *,
    include_user_effects: bool = True,
) -> tuple[argparse.ArgumentParser, dict[str, tuple[type[BaseEffect], type[BaseConfig]]]]:
    """Build the CLI parser and discover available effects.

    This registers built-in effect modules and, when requested, user-provided
    effect modules from the XDG config effects directory and `TTE_DEV_EFFECTS_DIR`. It returns the parsed
    CLI parser together with a mapping of effect command names to their effect
    and config classes.

    A user effect module in the XDG config effects directory that fails to import or register is
    skipped with a warning on standard error. Failures in built-in and development effect modules
    are raised.

    Args:
        include_user_effects: Whether to load external effects, including opted-in development effects.

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

    for module_info in pkgutil.iter_modules(
        terminaltexteffects.effects.__path__,
        terminaltexteffects.effects.__name__ + ".",
    ):
        if not include_user_effects and module_info.name == "terminaltexteffects.effects.effect_dev":
            continue
        module = importlib.import_module(module_info.name)
        _register_effect_from_module(module)

    plugins_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "terminaltexteffects" / "effects"
    if include_user_effects:
        _release_sibling_import_names()
        for plugin_file, module_name in _external_effect_files(plugins_dir, _USER_EFFECT_MODULE_PREFIX):
            _register_user_effect(plugin_file, module_name, subparsers, effect_resource_map)
        development_dir = os.environ.get("TTE_DEV_EFFECTS_DIR")
        if development_dir is not None:
            directory = Path(development_dir).expanduser().resolve()
            if not development_dir or not directory.is_dir():
                msg = f"TTE_DEV_EFFECTS_DIR must name an existing directory: {development_dir!r}"
                raise ValueError(msg)
            for plugin_file, module_name in _external_effect_files(directory, _DEV_EFFECT_MODULE_PREFIX):
                _register_effect_from_module(_load_external_module(plugin_file, module_name))

    return parser, effect_resource_map


def build_parsers_and_parse_args() -> tuple[argparse.Namespace, dict[str, tuple[type[BaseEffect], type[BaseConfig]]]]:
    """Build the CLI parser, discover available effects, and parse arguments."""
    preliminary = _build_global_parser(add_help=False)
    preliminary.add_argument("effect_arguments", nargs=argparse.REMAINDER)
    global_args, _ = preliminary.parse_known_args()
    include_user_effects = global_args.print_completion is None
    parser, effect_resource_map = build_parser(include_user_effects=include_user_effects)
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


def _print_replays(
    effect: BaseEffect,
    iterator: Iterator[str],
    terminal: Terminal,
    count: int,
    next_playback_factory: Callable[[], tuple[BaseEffect, Iterator[str]]] | None = None,
) -> None:
    """Print fresh playbacks, stopping on empty output or after `count` runs.

    A zero `count` repeats until interrupted. The first iterator is constructed
    before opening terminal output so input validation remains fail-fast. When
    `next_playback_factory` is provided, it creates a newly selected effect and
    iterator for each completed playback.
    """
    completed = 0
    while True:
        rendered = False
        for frame in iterator:
            terminal.print(frame)
            rendered = True
        completed += 1
        if not rendered or (count and completed >= count):
            return
        if next_playback_factory is None:
            iterator = iter(effect)
        else:
            effect, iterator = next_playback_factory()


def main() -> None:
    """Run the terminaltexteffects command line interface.

    Parse CLI arguments, load input text, choose and configure the requested effect,
    and stream rendered frames to the terminal. Empty or whitespace-only input is
    a successful no-op. The process exits with status `1` for invalid effect
    selection, input file read failures, or keyboard interruption.
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
    if args.input_file:
        try:
            input_data = Path(args.input_file).read_text(encoding="UTF-8")
        except FileNotFoundError:
            print(f"File not found: {args.input_file}")
            sys.exit(1)
        except Exception as e:  # noqa: BLE001
            print(f"Error reading file: {args.input_file} - {e}")
            sys.exit(1)
    else:
        input_data = Terminal.get_piped_input()
    if not input_data.strip():
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
        sys.exit(1)

    terminal_config = TerminalConfig._build_config(args)

    assert selected_effect_name is not None
    effect = _create_effect(
        selected_effect_name,
        input_data,
        effect_resource_map,
        terminal_config,
        None if args.random_effect else args,
    )
    try:
        effect_iterator = iter(effect)
        with effect.terminal_output() as terminal:
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
            _print_replays(effect, effect_iterator, terminal, args.repeat, next_playback_factory)
    except (EmptyInputError, UnsupportedAnsiSequenceError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == "__main__":
    main()
