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

### Recording and playback

Use `--record FILE` to render an effect once and save its frames, then `--play` to replay them without
running the effect again. Playback uses far less CPU than rendering, which suits screensavers, background
displays, and slower hardware that cannot render an effect at full frame rate. Recordings use the `.tterec`
extension.

```bash title="Record an effect, then play it until Ctrl+C"
tte -i banner.txt --record banner.tterec --canvas-width 0 --canvas-height 0 matrix
tte --play banner.tterec --repeat 0
```

Recording renders frames as fast as possible and shows nothing; it prints a one-line summary to standard
error when it finishes. `--frame-rate` must be greater than `0` and becomes the playback rate. Effect
phases measured in seconds, such as `matrix --rain-time` and `thunderstorm --storm-time`, last the same
number of frames as they would live, so a recording plays for the intended length. Random choices are
captured as they occur; pass `--seed` to make a recording reproducible. `--repeat COUNT` and
`--random-effect` record a sequence of playbacks into one file; `--repeat 0` is not accepted when recording.
An interrupted or failed recording leaves no partial file, and an existing file at the path is replaced only
when recording completes.

A recording stores only the canvas. Canvas size, text anchoring, and color options such as `--xterm-colors`
and `--no-color` are fixed when recording. Set `--canvas-width` and `--canvas-height` explicitly, or use `0`
to match the terminal at recording time, so the recording does not depend on the input size.

`--play PATH` takes a recording file or a directory. For a directory, every top-level `.tterec` file plays
in filename order; other files and subdirectories are ignored. No effect name or input is needed, and
standard input is not read. Every recording is fully validated before anything is shown, and any invalid
recording is an error. Playback options:

- `--repeat COUNT` repeats the file or directory (`0` repeats until Ctrl+C).
- `--frame-rate` overrides the recorded frame rate; `0` plays as fast as possible.
- `--hold SECONDS` keeps the last frame of each recording on screen before the next recording or repeat
  (0 to 86400 seconds).
- `--shuffle` plays a directory in random order, reshuffled each repeat; `--seed` makes the order repeatable.
- `--alt-screen` plays in the terminal's alternate screen, like full-screen programs such as `less`, and
  restores the original screen and scrollback when playback ends.
- `--anchor-canvas` positions the recording in the terminal. Recordings of different sizes in one directory
  share a canvas sized to the largest, each anchored within it.
- `--seed`, `--reuse-canvas`, `--no-eol`, and `--no-restore-cursor` work as they do for live effects.

Options fixed when a recording is made cannot be used with `--play`, and are rejected with an error naming
them: `--canvas-width`, `--canvas-height`, `--anchor-text`, `--xterm-colors`, `--no-color`,
`--terminal-background-color`, `--existing-color-handling`, `--tab-width`, `--wrap-text`, and
`--ignore-terminal-dimensions`. The effect-selection filters `--include-effects` and `--exclude-effects` are
rejected too. An effect name, `--random-effect`, and `--input-file` cannot be combined with `--play`. To
change any of these, record again.

Playback exits with an error if the terminal is smaller than the recorded canvas. Recordings are treated
as untrusted input: playback writes only text and color (SGR) sequences, and rejects any recording that
contains other control or escape sequences, has rows that do not exactly fill the recorded canvas width, or
is corrupt, truncated, or oversized. Text attributes are reset when playback ends. A recording that changes
on disk after validation stops playback with an error. Recordings larger than 256 MiB are not held in memory;
on later passes each of their frames is checked again as it plays. A replacement with another valid
recording with the same canvas size, frame rate, and TTE version therefore plays without an error, and one
that is corrupt near its end can show earlier frames before playback stops. Playback ends early when a pass
contains no frames.

```bash title="Background display from a directory of recordings"
tte --play ~/recordings --repeat 0 --shuffle --hold 5 --alt-screen
```

Recording and playback are part of development toward 0.16.0 and are not available in the published 0.15.0
package.

Custom effect modules are discovered from `${XDG_CONFIG_HOME}/terminaltexteffects/effects`, or
`~/.config/terminaltexteffects/effects` when `XDG_CONFIG_HOME` is unset, empty, or a relative path. Any `.py` file in that directory that
provides `get_effect_resources()` can register an effect command alongside the built-in effects.
If a custom effect module fails to import or register, TTE prints a warning naming the file to standard
error, skips that module, and keeps the built-in effects and other valid custom effects available.
Each module is imported under its file name, so custom effect modules can import themselves and earlier-loaded
sibling files by name. A file named like a standard-library or installed module, such as `random.py`, is skipped
with a warning instead of replacing that module; rename the file to load it.
These skip-with-warning protections are part of development toward 0.16.0. In the published 0.15.0 package,
a custom effect module that fails to import or register stops `tte` from starting, and a module named like an
installed module can replace it.

For prototypes in an unreleased checkout, set `TTE_DEV_EFFECTS_DIR` to a directory of effect
modules. These modules use the same `get_effect_resources()` interface. This development-only
setting is not available in the released 0.15.0 CLI, is explicit, and does not affect bundled
shell completion generation. Contributors can use `python -m tools.dev <effect>` from a checkout
to load its `dev_effects/` directory.

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

## Community effects

TTE 0.15.0 and later can load community effect modules without installing them into the TTE package.
Download or clone the effect author's source, then place the flat effect `.py` module in
`${XDG_CONFIG_HOME:-$HOME/.config}/terminaltexteffects/effects`. On macOS and Linux, for example:

```bash title="Install a community effect module"
mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/terminaltexteffects/effects"
cp path/to/community_effect.py "${XDG_CONFIG_HOME:-$HOME/.config}/terminaltexteffects/effects/"
```

These commands use `XDG_CONFIG_HOME` as written. If it is set to a relative path, unset it or set it to an
absolute directory before running them; TTE ignores relative values and searches `~/.config` instead.
On TTE 0.15.0, an empty `XDG_CONFIG_HOME` also does not fall back to `~/.config`, so unset an empty value too.

Install any dependencies listed by the author into the same Python environment as TTE. The module
must expose `get_effect_resources()` and use APIs supported by the TTE version you have installed.
Check the author's stated supported TTE version, license, and installation notes before running it;
external effect modules execute as Python code in your environment. Then inspect its options and run it
like a built-in effect:

```bash title="Inspect and run a community effect"
tte community-effect -h
printf 'Hello!\n' | tte community-effect
```

Replace `community-effect` with the effect command name documented by its author.
On TTE 0.15.0, a module that fails to load stops `tte` from starting; remove it from the effects
directory to restore the built-in effects.
The effect remains hosted and maintained by its author.

Browse or share projects in the [TTE Effect Show and Tell discussion category](https://github.com/ChrisBuilds/terminaltexteffects/discussions/categories/tte-effect-show-and-tell).
Include a short demo, a source repository or public Gist, supported TTE version, installation and run
steps, license, and maintenance status. A listing is a community sharing post; it does not mean the
effect is bundled with TTE or endorsed by its maintainers.

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
