# Application Guide

When used as a system application, TerminalTextEffects will produce animations on text passed to stdin or through the
`-i` argument. Passing data via STDIN to TTE occurs via pipes or redirection.

## Invocation Examples

=== "Piping"

    ```bash title="Piping directory listing output through TTE"
    ls -latr | tte slide
    ```

=== "Redirection"

    ```bash title="Redirecting a file through TTE"
    tte slide < your_file
    ```

=== "File Input"

    ```bash title="Passing a file argument to TTE"
    tte -i path/to/file slide
    ```

## Configuration

TTE has many global terminal configuration options as well as effect-specific configuration options available via command-line arguments.

Terminal configuration options should be specified prior to providing the effect name. The basic format is as follows:

```bash title="TTE usage syntax"
tte [global_options] <effect_name> [effect_options]
```

Using the `-h` argument in place of the global_options or effect_options will produce either the global or effect help output, respectively.

Shell completions for bundled effects are also available for Bash, Zsh, and PowerShell 7+:

Run `tte --print-completion` to print copy-and-paste setup commands, or use the commands directly:

```bash title="Generate shell completions"
eval "$(tte --print-completion bash)"
```

```bash title="Generate zsh completions"
eval "$(tte --print-completion zsh)"
```

```powershell title="Enable PowerShell 7 completion in this session"
tte --print-completion powershell | Out-String | Invoke-Expression
```

The script registers both `tte` and `terminaltexteffects`. It completes built-in effect names,
global and effect-specific options, allowed values, and input-file paths. Bundled completions
exclude user plugins and development effects and require no Python process on each Tab press.

To enable completions for future shells, add the relevant command to your `~/.bashrc` or `~/.zshrc`.
For PowerShell 7+, add the activation command above to your `$PROFILE` file, creating its
parent directory/file if needed, then restart PowerShell. Setup is opt-in; TTE never edits
profiles automatically. Remove that profile line and restart the shell to disable completion.

On Windows, Windows Terminal handles rendering and may host PowerShell, Command Prompt,
or WSL shells. Choose PowerShell 7 for this script; Windows PowerShell 5.1 is not supported.
Bash/Zsh sessions continue to use their respective scripts. Completion reads literal arguments;
it does not evaluate variables or subexpressions to infer context.
Completion includes valid values for enum-like options such as gradient directions, grouping modes, and easing
functions.
Completion scripts cover built-in effects only; options from custom effect plugins are not included.

TTE can randomly select an effect with `--random-effect`/`-R`. Use `--seed` to make that selection repeatable, or
limit the pool with `--include-effects` and `--exclude-effects`:

```bash title="Random effect selection"
ls | tte --random-effect --seed 123 --include-effects beams decrypt rain
```

Use `--repeat COUNT` to play effects in cycles against the same input. The default is one playback;
`--repeat 3` plays three times, and `--repeat 0` keeps replaying until you press Ctrl+C.
Each playback starts a fresh effect iterator, without storing frames. With `--random-effect`, a new
effect is selected from the available pool for each playback, respecting `--include-effects` and
`--exclude-effects`; the same effect may be selected consecutively. `--seed` makes the selection
sequence repeatable. Randomly selected effects use their default configuration. Empty input remains
a no-op, and an effect that produces no frames stops rather than spinning indefinitely.

```bash title="Repeat an animation"
printf 'Hello!' | tte --repeat 3 wipe
```

```bash title="Continuous animation until Ctrl+C"
tte -i banner.txt --repeat 0 beams
```

Custom effect modules are discovered from `${XDG_CONFIG_HOME}/terminaltexteffects/effects`, or
`~/.config/terminaltexteffects/effects` when `XDG_CONFIG_HOME` is not set. Any `.py` file in that directory that
provides `get_effect_resources()` can register an effect command alongside the built-in effects.

For prototypes kept outside the shipped package, set `TTE_DEV_EFFECTS_DIR` to a directory of
effect modules. These modules use the same `get_effect_resources()` interface. The setting
is explicit and does not affect bundled shell completion generation. Contributors can use
`python -m tools.dev <effect>` from a checkout to load its `dev_effects/` directory.

The example below will pass the output of the `ls` command to TTE with the following options:

* *Global* options:
    - Text will be wrapped if wider than the terminal.
    - Tabs will be replaced with 4 spaces.

* *Effect* options:
    - Use the [slide](./effects/slide.md) effect.
    - Merge the groups.
    - Set movement-speed to 2.
    - Group by column.

```bash title="TTE argument specification example"
ls | tte --wrap-text --tab-width 4 slide --merge --movement-speed 2 --grouping column
```

## Example Usage

Animate fetch output on shell launch using screenfetch:

```bash title="Shell Fetch"
screenfetch -N | tte slide --merge
```

![fetch_demo](./img/application_demos/fetch_example.gif)

!!! note

    TTE is not a full terminal emulator, but it does parse common fetch-style input. Supported input includes
    SGR foreground/background colors, common cursor movement CSI sequences, carriage returns, and selected DEC
    private mode toggles for cursor visibility and line wrapping. Unsupported control sequences still fail fast with
    an error so they do not leak into the rendered animation.

## Short reproducible CLI example

Run this command in Bash (including Git Bash) or a compatible POSIX shell. It pipes literal
input into Wipe, fixes the canvas, and disables colors and playback delay. Global options
precede the effect name; effect options follow it. The animation ends with `Hi`.

<!-- tte-example: cli-wipe -->
```bash
printf 'Hi' | tte --seed 16 --frame-rate 0 --no-color \
  --canvas-width 2 --canvas-height 1 --ignore-terminal-dimensions \
  wipe --final-gradient-stops ffffff --final-gradient-steps 1 --final-gradient-frames 1
```

This is a short integration example rather than a pacing demonstration. For normal playback,
choose a nonzero frame rate or omit `--frame-rate`. CI executes this marked command directly
from this page and checks rendering and cursor restoration. It does not evaluate terminal
appearance; visual QA remains separate.
