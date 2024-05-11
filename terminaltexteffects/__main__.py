import argparse
import importlib
import pkgutil

import terminaltexteffects.effects
import terminaltexteffects.engine.terminal as term
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.utils.argsdataclass import ArgsDataClass


def main():
    parser = (argparse.ArgumentParser)(
        prog="terminaltexteffects",
        description="Apply visual effects to terminal text piped in from stdin.",
        epilog="Ex: ls -a | python -m terminaltexteffects decrypt --typing-speed 2 --ciphertext-colors 008000 00cb00 00ff00 --final-gradient-stops eda000 --final-gradient-steps 12 --final-gradient-direction vertical",
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
        terminal_config = TerminalConfig._from_parsed_args_mapping(args, TerminalConfig)
        effect_config = ArgsDataClass._from_parsed_args_mapping(args)
        effect_class = effect_config.get_effect_class()
        terminal_config.use_terminal_dimensions = True
        effect = effect_class(input_data)
        effect.effect_config = effect_config
        effect.terminal_config = terminal_config
        with effect.terminal_output() as terminal:
            for frame in effect:
                terminal.print(frame)


if __name__ == "__main__":
    main()
