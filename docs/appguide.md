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

Shell completions are also available for bash and zsh:

```bash title="Generate shell completions"
eval "$(tte --print-completion bash)"
```

```bash title="Generate zsh completions"
eval "$(tte --print-completion zsh)"
```

To enable completions for future shells, add the relevant command to your `~/.bashrc` or `~/.zshrc`.
If you add or remove custom effect plugins from `~/.config/terminaltexteffects/effects`, regenerate the completion
script so the available effect names stay in sync.

TTE can randomly select an effect with `--random-effect`/`-R`. Use `--seed` to make that selection repeatable, or
limit the pool with `--include-effects` and `--exclude-effects`:

```bash title="Random effect selection"
ls | tte --random-effect --seed 123 --include-effects beams decrypt rain
```

Custom effect modules are discovered from `${XDG_CONFIG_HOME}/terminaltexteffects/effects`, or
`~/.config/terminaltexteffects/effects` when `XDG_CONFIG_HOME` is not set. Any `.py` file in that directory that
provides `get_effect_resources()` can register an effect command alongside the built-in effects.

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
