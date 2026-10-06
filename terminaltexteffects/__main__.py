"""Package entry point for the TerminalTextEffects command line interface."""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import os
import pkgutil
import random
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import TYPE_CHECKING, cast

import terminaltexteffects.effects
from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.utils.exceptions import EmptyInputError, UnsupportedAnsiSequenceError
from terminaltexteffects.utils.shell_completion import (
    get_completion_instructions,
    get_completion_script,
    parse_completion_shell,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from importlib.machinery import SourceFileLoader
    from types import ModuleType

    from terminaltexteffects.engine.base_config import BaseConfig
    from terminaltexteffects.engine.base_effect import BaseEffect


def _external_effect_modules(directory: Path, prefix: str = "") -> Iterator[ModuleType]:
    """Load flat external modules deterministically without altering the import path."""
    for plugin_file in sorted(directory.glob("*.py")):
        if plugin_file.name == "__init__.py":
            continue
        module_name = prefix + plugin_file.stem
        spec = importlib.util.spec_from_file_location(module_name, plugin_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            # Flat .py paths resolve to SourceFileLoader; typeshed also permits legacy loaders.
            cast("SourceFileLoader", spec.loader).exec_module(module)
            yield module


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

    Args:
        include_user_effects: Whether to load external effects, including opted-in development effects.

    Returns:
        tuple[argparse.ArgumentParser, dict[str, tuple[type[BaseEffect], type[BaseConfig]]]]: The CLI parser and a
            mapping of effect names to their classes and configurations.

    Raises:
        ValueError: If two discovered effect modules register the same effect command.

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
        for module in _external_effect_modules(plugins_dir):
            _register_effect_from_module(module)
        development_dir = os.environ.get("TTE_DEV_EFFECTS_DIR")
        if development_dir is not None:
            directory = Path(development_dir).expanduser().resolve()
            if not development_dir or not directory.is_dir():
                msg = f"TTE_DEV_EFFECTS_DIR must name an existing directory: {development_dir!r}"
                raise ValueError(msg)
            for module in _external_effect_modules(directory, "_tte_dev_"):
                _register_effect_from_module(module)

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
        effect_iterator = iter(effect)
        with effect.terminal_output() as terminal:
            for frame in effect_iterator:
                terminal.print(frame)
    except (EmptyInputError, UnsupportedAnsiSequenceError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == "__main__":
    main()
