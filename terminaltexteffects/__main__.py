import argparse
import importlib
import pkgutil

import terminaltexteffects.effects
import terminaltexteffects.utils.terminal as term
from terminaltexteffects.utils.argsdataclass import ArgsDataClass
from terminaltexteffects.utils.terminal import TerminalConfig


def main():
    parser = (argparse.ArgumentParser)(
        prog="terminaltexteffects",
        description="Apply visual effects to terminal text piped in from stdin.",
        epilog="Ex: ls -a | python -m terminaltexteffects --xterm-colors decrypt -a 0.002 --ciphertext-color 00ff00 --plaintext-color ff0000 --final-color 0000ff",
    )

    TerminalConfig._add_args_to_parser(parser)

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
            args_class._add_to_args_subparsers(subparsers)

    args = parser.parse_args()
    input_data = term.Terminal.get_piped_input()
    if not input_data.strip():
        print("NO INPUT.")
    else:
        try:
            terminal_config = TerminalConfig._from_parsed_args_mapping(args, TerminalConfig)
            effect_config = ArgsDataClass._from_parsed_args_mapping(args)
            effect_class = effect_config.get_effect_class()
            terminal_config.use_terminal_dimensions = True
            effect = effect_class(input_data, effect_config, terminal_config)
            effect.build()
            effect.terminal.prep_outputarea()
            for frame in effect:
                effect.terminal.print(frame)
        finally:
            effect.terminal.restore_cursor()


if __name__ == "__main__":
    main()
