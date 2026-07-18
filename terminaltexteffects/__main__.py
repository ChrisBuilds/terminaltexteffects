"""Package entry point for the TerminalTextEffects command line interface."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import os
import pkgutil
import random
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import TYPE_CHECKING

import terminaltexteffects.effects
from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.utils.exceptions import UnsupportedAnsiSequenceError
from terminaltexteffects.utils.shell_completion import SUPPORTED_SHELLS, get_completion_script

if TYPE_CHECKING:
    from types import ModuleType

    from terminaltexteffects.engine.base_config import BaseConfig
    from terminaltexteffects.engine.base_effect import BaseEffect


def _get_effect_resources(
    module: ModuleType,
) -> tuple[str, type[BaseEffect], type[BaseConfig]] | None:
    """Return validated effect resources from a module when provided."""
    if not hasattr(module, "get_effect_resources"):
        return None
    resources = module.get_effect_resources()
    if not isinstance(resources, tuple) or len(resources) != 3:
        msg = "get_effect_resources() must return a three-item tuple"
        raise ValueError(msg)
    return resources


def _register_effect_resources(
    resources: tuple[str, type[BaseEffect], type[BaseConfig]],
    subparsers: argparse._SubParsersAction,
    effect_resource_map: dict[str, tuple[type[BaseEffect], type[BaseConfig]]],
) -> None:
    """Register effect resources and populate their CLI options.

    The configuration parser is populated before the resource map is mutated so a
    parser failure cannot leave an effect command that is not invokable.

    Raises:
        ValueError: If the effect command has already been registered.

    """
    effect_cmd, effect_class, config_class = resources
    if effect_cmd in effect_resource_map:
        msg = f"Duplicate effect command detected: {effect_cmd}"
        raise ValueError(msg)
    previous_choices = dict(subparsers.choices)
    previous_choice_actions = list(subparsers._choices_actions)
    parser_populated = False
    try:
        config_class._populate_parser(subparsers)
        parser_populated = True
    finally:
        if not parser_populated:
            subparsers.choices.clear()
            subparsers.choices.update(previous_choices)
            subparsers._choices_actions[:] = previous_choice_actions
    effect_resource_map[effect_cmd] = (effect_class, config_class)


def _validate_user_effect_resources(
    resources: tuple[str, type[BaseEffect], type[BaseConfig]],
    effect_resource_map: dict[str, tuple[type[BaseEffect], type[BaseConfig]]],
) -> None:
    """Validate user resources against disposable parser state."""
    effect_cmd, _, config_class = resources
    if not isinstance(effect_cmd, str) or not effect_cmd:
        msg = "Effect command must be a non-empty string"
        raise ValueError(msg)
    if effect_cmd in effect_resource_map:
        msg = f"Duplicate effect command detected: {effect_cmd}"
        raise ValueError(msg)
    parser_spec = config_class.parser_spec
    if parser_spec.name != effect_cmd:
        msg = f"Effect command '{effect_cmd}' does not match parser command '{parser_spec.name}'"
        raise ValueError(msg)


def _warn_user_plugin(plugin_file: Path, exc: Exception) -> None:
    """Write a non-fatal user plugin warning to stderr."""
    print(
        f"Warning: Failed to load user effect plugin '{plugin_file}': {type(exc).__name__}: {exc}",
        file=sys.stderr,
    )


def _load_user_effect_module(plugin_file: Path, module_name: str) -> ModuleType:
    """Load one user effect module under its collision-safe module name."""
    spec = importlib.util.spec_from_file_location(module_name, plugin_file)
    if spec is None or spec.loader is None:
        msg = "Unable to create a module specification"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _register_discovered_effects(
    subparsers: argparse._SubParsersAction,
    effect_resource_map: dict[str, tuple[type[BaseEffect], type[BaseConfig]]],
) -> None:
    """Register built-in effects and isolate failures in user effect plugins."""
    for module_info in pkgutil.iter_modules(
        terminaltexteffects.effects.__path__,
        terminaltexteffects.effects.__name__ + ".",
    ):
        module = importlib.import_module(module_info.name)
        resources = _get_effect_resources(module)
        if resources is not None:
            _register_effect_resources(resources, subparsers, effect_resource_map)

    plugins_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "terminaltexteffects" / "effects"
    if not plugins_dir.exists():
        return

    for plugin_file in sorted(plugins_dir.glob("*.py")):
        if plugin_file.name == "__init__.py":
            continue
        path_digest = hashlib.sha256(str(plugin_file.resolve()).encode()).hexdigest()[:12]
        module_name = f"_terminaltexteffects_user_effect_{plugin_file.stem}_{path_digest}"
        try:
            module = _load_user_effect_module(plugin_file, module_name)
            resources = _get_effect_resources(module)
            if resources is not None:
                _validate_user_effect_resources(resources, effect_resource_map)
                _register_effect_resources(resources, subparsers, effect_resource_map)
        except Exception as exc:  # noqa: BLE001
            sys.modules.pop(module_name, None)
            _warn_user_plugin(plugin_file, exc)


def build_parser() -> tuple[argparse.ArgumentParser, dict[str, tuple[type[BaseEffect], type[BaseConfig]]]]:
    """Build the CLI parser and discover available effects.

    This includes registering built-in effect modules and valid user-provided effect
    modules from the XDG config effects directory. User modules that fail to import
    or register are skipped with a warning to standard error.

    Returns:
        tuple[argparse.ArgumentParser, dict[str, tuple[type[BaseEffect], type[BaseConfig]]]]: The CLI parser and a
            mapping of effect names to their classes and configurations.

    Raises:
        ValueError: If built-in effect modules register the same effect command.

    """
    parser = argparse.ArgumentParser(
        prog="tte",
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
        choices=SUPPORTED_SHELLS,
        help="Print a shell completion script for the requested shell and exit.",
    )
    parser.add_argument("--random-effect", "-R", action="store_true", help="Randomly select an effect to apply")
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

    subparsers = parser.add_subparsers(
        title="Effect",
        description="Name of the effect to apply. Use <effect> -h for effect specific help.",
        help="Available Effects",
        required=False,
        dest="effect",
    )

    effect_resource_map: dict[str, tuple[type[BaseEffect], type[BaseConfig]]] = {}

    _register_discovered_effects(subparsers, effect_resource_map)

    return parser, effect_resource_map


def build_parsers_and_parse_args() -> tuple[argparse.Namespace, dict[str, tuple[type[BaseEffect], type[BaseConfig]]]]:
    """Build the CLI parser, discover available effects, and parse arguments."""
    parser, effect_resource_map = build_parser()
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


def main() -> None:
    """Run the terminaltexteffects command line interface.

    Parse CLI arguments, load input text, choose and configure the requested effect,
    and stream rendered frames to the terminal. The process exits with status `1`
    for missing input, invalid effect selection, input file read failures, or
    keyboard interruption.
    """
    args, effect_resource_map = build_parsers_and_parse_args()
    if args.print_completion:
        parser, _ = build_parser()
        print(get_completion_script(args.print_completion, parser), end="")
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
        print("NO INPUT.")
        sys.exit(1)

    if args.random_effect:
        if args.include_effects:
            available_effects = [effect for effect in effect_resource_map if effect in args.include_effects]
        elif args.exclude_effects:
            available_effects = [effect for effect in effect_resource_map if effect not in args.exclude_effects]
        else:
            available_effects = list(effect_resource_map)
        if not available_effects:
            print("Error: No effects available for random selection based on include/exclude filters.\n")
            sys.exit(1)

        args.effect = random.choice(available_effects)
    elif not args.effect:
        print("Error: No effect specified. Must specify an effect or use --random-effect.\n")
        sys.exit(1)

    effect_class, effect_config_class = effect_resource_map[args.effect]
    terminal_config = TerminalConfig._build_config(args)
    effect_config = effect_config_class._build_config(None if args.random_effect else args)
    effect = effect_class(input_data, effect_config, terminal_config)
    try:
        with effect.terminal_output() as terminal:
            for frame in effect:
                terminal.print(frame)
    except UnsupportedAnsiSequenceError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == "__main__":
    main()
