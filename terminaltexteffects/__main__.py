import argparse
import importlib
import pkgutil
import sys

import terminaltexteffects.effects
import terminaltexteffects.utils.terminal as term
import terminaltexteffects.utils.ansitools as ansitools
import terminaltexteffects.utils.argtypes as argtypes


def main():
    parser = (argparse.ArgumentParser)(
        prog="terminaltexteffects",
        description="Apply visual effects to terminal text piped in from stdin.",
        epilog="Ex: ls -a | python -m terminaltexteffects --xterm-colors decrypt -a 0.002 --ciphertext-color 00ff00 --plaintext-color ff0000 --final-color 0000ff",
    )
    parser.add_argument(
        "--xterm-colors",
        action="store_true",
        help="Convert any colors specified in RBG hex to the closest XTerm-256 color.",
        default=False,
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable all colors in the effect.",
        default=False,
    )
    parser.add_argument(
        "--tab-width",
        type=argtypes.positive_int,
        help="Number of spaces to use for a tab character.",
        default=4,
    )
    parser.add_argument(
        "--no-wrap",
        action="store_true",
        help="Disable wrapping of text.",
        default=False,
    )
    subparsers = parser.add_subparsers(
        title="Effect",
        description="Name of the effect to apply. Use <effect> -h for effect specific help.",
        help="Available Effects",
        required=True,
    )

    discovered_effects = [
        importlib.import_module(module.name)
        for module in pkgutil.iter_modules(
            terminaltexteffects.effects.__path__, terminaltexteffects.effects.__name__ + "."
        )
    ]

    for effect in discovered_effects:
        effect.add_arguments(subparsers)

    args = parser.parse_args()
    input_data = term.Terminal.get_piped_input()
    if not input_data.strip():
        print("NO INPUT.")
    else:
        try:
            terminal = term.Terminal(input_data, args)
            effect = args.effect_class(terminal, args)
            effect.run()
        except Exception as e:
            raise Exception(f"Error running effect: {e}")
        finally:
            sys.stdout.write(ansitools.SHOW_CURSOR())


if __name__ == "__main__":
    main()
