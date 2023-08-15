import importlib
import pkgutil
import terminaltexteffects.utils.terminaloperations as tops

discovered_plugins = {
    name: importlib.import_module(name)
    for finder, name, ispkg in pkgutil.iter_modules(["./effects"])
    if name.startswith("effect_")
}
print(discovered_plugins)


def main():
    input_data = tops.get_piped_input()
    if not input_data:
        print("NO INPUT.")
    else:
        pass


if __name__ == "__main__":
    main()
