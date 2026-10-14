# Discovery and loading

Every time `tte` starts, it finds the available effects, imports their modules, and builds a subcommand for each one.
This chapter explains where TTE looks, what a module needs to be loaded, and what happens when loading fails.

## What makes a module an effect

TTE treats a Python module as an effect if it has a module-level `get_effect_resources()` function that returns three
things:

```python
def get_effect_resources() -> tuple[str, type[BaseEffect], type[BaseConfig]]:
    return "myspray", MySpray, MySprayConfig
```

1. The command name, as typed after `tte`. It must match `parser_spec.name` in the configuration class.
2. The effect class, a subclass of `BaseEffect`.
3. The configuration class, a subclass of `BaseConfig`.

TTE adds the command, with options built from the configuration class (see
[Configuration and the CLI](configuration.md)). When the user runs the command, TTE creates the effect class with the
input text and the parsed configuration, and prints the frames its iterator produces. A module without
`get_effect_resources()` is imported but adds no command.

## Where TTE looks

TTE loads effects from three places, in this order:

| Where | What is loaded |
| --- | --- |
| The `terminaltexteffects.effects` package | The built-in effects. |
| The community effects directory | Every `.py` file in `${XDG_CONFIG_HOME:-$HOME/.config}/terminaltexteffects/effects`. |
| `TTE_DEV_EFFECTS_DIR`, if set | Every `.py` file in that directory. For development; see below. |

Files are loaded in name order. Subdirectories and `__init__.py` are ignored, so a community effect is a single flat
`.py` file. If `XDG_CONFIG_HOME` is unset, empty, or a relative path, TTE uses `~/.config`.

Every module is imported on every run, even when the user runs a different effect, because TTE needs every
configuration class to build its command-line parser. Keep module-level code to imports and definitions: do the
effect's work in the iterator, and avoid slow imports at the top of the module.

## Community effects

The community effects directory is where users install effects, and where you develop yours. Each file is imported
under its file name, so `myspray.py` becomes the module `myspray`. A module in that directory can import sibling files
that were loaded before it by name, but keeping an effect in one file makes it easier to share.

TTE protects the rest of the CLI from a broken community effect. If a module fails to import, raises an error from
`get_effect_resources()`, or registers a command that already exists, TTE prints a warning naming the file to standard
error, skips that module, and runs normally:

```text
Warning: Skipping user effect plugin '/home/me/.config/terminaltexteffects/effects/broken.py': ModuleNotFoundError: No module named 'not_a_real_package'
Warning: Skipping user effect plugin '/home/me/.config/terminaltexteffects/effects/dupe.py': ValueError: Duplicate effect command detected: spray
Warning: Skipping user effect plugin '/home/me/.config/terminaltexteffects/effects/random.py': ImportError: Module name 'random' is already used by an installed or loaded module; rename the file
```

The last warning shows a naming rule: a file named like a standard-library or installed module is skipped, rather than
replacing that module. Name your file after your effect, and pick a command name no built-in effect uses. Built-in
effects are loaded first, so they always win a conflict, which is why the tutorial's command is `myspray` and not
`spray`.

If your effect doesn't appear in `tte -h`, look for one of these warnings at the top of the output.

## Development effects

`TTE_DEV_EFFECTS_DIR` points TTE at a directory of effect modules in progress, without copying them into the community
effects directory:

```bash
TTE_DEV_EFFECTS_DIR="$PWD/my_effects" tte --input-file concept_input.txt glow
```

Development modules follow the same rules, with two differences meant to surface problems early:

- A failure stops `tte` with the error, instead of a warning.
- Each module is imported under a private prefixed name, so development modules can't import each other by file name.

The variable must name an existing directory. In a TTE repository checkout, maintainers put unfinished built-in effects
in `dev_effects/` and run them with `python -m tools.dev <effect>`, which sets this variable for that directory.

## Where to go next

- [Tutorial step 1: Scaffold](../tutorial/01-scaffold.md) creates and loads the first version of MySpray.
- [Configuration and the CLI](configuration.md) covers the configuration class that `get_effect_resources()` returns.
