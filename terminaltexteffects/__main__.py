import importlib
import terminaltexteffects.effects
import pkgutil
import terminaltexteffects.utils.terminaloperations as tops

discovered_effects = {
    name: importlib.import_module(name)
    for finder, name, ispkg in pkgutil.iter_modules(
        terminaltexteffects.effects.__path__, terminaltexteffects.effects.__name__ + "."
    )
}


def main():
    input_data = tops.get_piped_input()
    if not input_data:
        print("NO INPUT.")
    else:
        pass


if __name__ == "__main__":
    main()
