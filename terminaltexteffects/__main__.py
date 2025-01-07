"""Provides the command line interface for the TerminalTextEffects application."""

from __future__ import annotations

import argparse
import importlib
import pkgutil
import sys
from pathlib import Path

import terminaltexteffects.effects
import terminaltexteffects.engine.terminal as term
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.argsdataclass import ArgsDataClass


def main() -> None:
    """Run the terminaltexteffects command line interface."""
    parser = (argparse.ArgumentParser)(
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

    TerminalConfig._add_args_to_parser(parser)

    subparsers = parser.add_subparsers(
        title="Effect",
        description="Name of the effect to apply. Use <effect> -h for effect specific help.",
        help="Available Effects",
        required=True,
    )

    for module_info in pkgutil.iter_modules(
        terminaltexteffects.effects.__path__,
        terminaltexteffects.effects.__name__ + ".",
    ):
        module = importlib.import_module(module_info.name)

        if hasattr(module, "get_effect_and_args"):
            effect_class, args_class = module.get_effect_and_args()
            args_class._add_to_args_subparsers(subparsers)

    args = parser.parse_args()
    if args.input_file:
        try:
            input_data = Path(args.input_file).read_text(encoding="UTF-8")
        except FileNotFoundError:
            print(f"File not found: {args.input_file}")
            return
        except Exception as e:  # noqa: BLE001
            print(f"Error reading file: {args.input_file} - {e}")
            return
    else:
        input_data = term.Terminal.get_piped_input()
    if not input_data.strip():
        print("NO INPUT.")
    else:
        terminal_config = TerminalConfig._from_parsed_args_mapping(args, TerminalConfig)
        effect_config = ArgsDataClass._from_parsed_args_mapping(args)
        effect_class = effect_config.get_effect_class()
        terminal_config.use_terminal_dimensions = True
        effect = effect_class(input_data)
        effect.effect_config = effect_config
        effect.terminal_config = terminal_config
        try:
            with effect.terminal_output() as terminal:
                for frame in effect:
                    terminal.print(frame)
        except KeyboardInterrupt:
            sys.exit(1)


if __name__ == "__main__":
    main()
