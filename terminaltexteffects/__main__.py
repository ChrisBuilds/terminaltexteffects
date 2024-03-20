import argparse
import importlib
import pkgutil
import sys

import terminaltexteffects.effects
import terminaltexteffects.utils.ansitools as ansitools
import terminaltexteffects.utils.terminal as term
from terminaltexteffects.utils.argsdataclass import ArgsDataClass
from terminaltexteffects.utils.terminal import TerminalArgs


def main():
    parser = (argparse.ArgumentParser)(
        prog="terminaltexteffects",
        description="Apply visual effects to terminal text piped in from stdin.",
        epilog="Ex: ls -a | python -m terminaltexteffects --xterm-colors decrypt -a 0.002 --ciphertext-color 00ff00 --plaintext-color ff0000 --final-color 0000ff",
    )

    TerminalArgs.add_args_to_parser(parser)

    subparsers = parser.add_subparsers(
        title="Effect",
        description="Name of the effect to apply. Use <effect> -h for effect specific help.",
        help="Available Effects",
        required=True,
    )

    for module_info in pkgutil.iter_modules(
        terminaltexteffects.effects.__path__, terminaltexteffects.effects.__name__ + "."
    ):
        module = importlib.import_module(module_info.name)

        if hasattr(module, "get_effect_and_args"):
            effect_class, args_class = tuple[any, ArgsDataClass](module.get_effect_and_args())
            args_class.add_to_args_subparsers(subparsers)

    args = parser.parse_args()
    input_data = term.Terminal.get_piped_input()
    if not input_data.strip():
        print("NO INPUT.")
    else:
        try:
            terminal_args = TerminalArgs.from_parsed_args_mapping(args, TerminalArgs)
            terminal = term.Terminal(input_data, terminal_args)
            effect_args = ArgsDataClass.from_parsed_args_mapping(args)
            effect_class = effect_args.get_effect_class()
            effect = effect_class(terminal, effect_args)
            effect.run()
        finally:
            sys.stdout.write(ansitools.SHOW_CURSOR())


if __name__ == "__main__":
    main()
