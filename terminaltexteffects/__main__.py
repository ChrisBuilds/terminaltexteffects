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


def main() -> None:
    """Run the terminaltexteffects command line interface."""
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

    TerminalConfig._populate_parser(parser)

    subparsers = parser.add_subparsers(
        title="Effect",
        description="Name of the effect to apply. Use <effect> -h for effect specific help.",
        help="Available Effects",
        required=True,
        dest="effect",
    )
    subparsers.add_parser(
        name="random_effect",
        help=(
            "Randomly select an effect to apply to the input text. All effect and effect-specific options are ignored."
        ),
        description=("Random effect."),
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
            effect_resource_map[effect_cmd] = (effect_class, config_class)
            config_class._populate_parser(subparsers)

    # check for random_effect subparser selection and replace
    # with an effect name prior to parsing, otherwise default
    # config options are not processed
    if "random_effect" in sys.argv:
        sys.argv[sys.argv.index("random_effect")] = random.choice(list(effect_resource_map.keys()))

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
        input_data = Terminal.get_piped_input()
    if not input_data.strip():
        print("NO INPUT.")
        return

    effect_class, effect_config_class = effect_resource_map[args.effect]
    terminal_config = TerminalConfig._build_config(args)
    effect_config = effect_config_class._build_config(args)
    effect = effect_class(input_data, effect_config, terminal_config)
    try:
        with effect.terminal_output() as terminal:
            for frame in effect:
                terminal.print(frame)
    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == "__main__":
    main()
