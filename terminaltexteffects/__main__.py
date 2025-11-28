"""Provides the command line interface for the TerminalTextEffects application."""

from __future__ import annotations

import argparse
import importlib
import pkgutil
import random
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import terminaltexteffects.effects
from terminaltexteffects.engine.terminal import Terminal, TerminalConfig

if TYPE_CHECKING:
    from terminaltexteffects.engine.base_config import BaseConfig
    from terminaltexteffects.engine.base_effect import BaseEffect


def build_parsers_and_parse_args() -> tuple[argparse.Namespace, dict[str, tuple[type[BaseEffect], type[BaseConfig]]]]:
    """Build the argument parsers for the terminaltexteffects CLI and parse the arguments.

    Returns:
        tuple[argparse.Namespace, dict[str, tuple[type[BaseEffect], type[BaseConfig]]]]: The parsed arguments and a
            mapping of effect names to their classes and configurations.

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
        version="TerminalTextEffects " + terminaltexteffects.__version__,
    )
    parser.add_argument("--random-effect", "-R", action="store_true", help="Randomly select an effect to apply")
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

    TerminalConfig._populate_parser(parser)

    subparsers = parser.add_subparsers(
        title="Effect",
        description="Name of the effect to apply. Use <effect> -h for effect specific help.",
        help="Available Effects",
        required=False,
        dest="effect",
    )

    effect_resource_map: dict[str, tuple[type[BaseEffect], type[BaseConfig]]] = {}
    for module_info in pkgutil.iter_modules(
        terminaltexteffects.effects.__path__,
        terminaltexteffects.effects.__name__ + ".",
    ):
        module = importlib.import_module(module_info.name)

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

    return parser.parse_args(), effect_resource_map


def main() -> None:
    """Run the terminaltexteffects command line interface."""
    args, effect_resource_map = build_parsers_and_parse_args()
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
    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == "__main__":
    main()
