# Installation

TerminalTextEffects can be installed as a system application, to run effects from your shell, or as a library, to
use effects in your Python code. The core package has no third-party dependencies.

## Requirements

| Version | Minimum Python |
| --- | --- |
| 0.15.0, the latest published release | 3.8 |
| Development `main`, toward 0.16.0 | 3.9.2 |

Effects use standard ANSI terminal sequences and work in most modern terminals. See
[Support and Compatibility](./support.md) for platform coverage and terminal requirements.

## System Application

When installed as an application, TerminalTextEffects can be called from the shell to produce effects on any input
piped to standard input. Uses include running it on shell launch, aliasing commands to pass their output through
TTE, and SSH login animations.

=== "pipx"

    ```bash
    pipx install terminaltexteffects
    ```

=== "uv"

    ```bash title="Install"
    uv tool install terminaltexteffects
    ```

    ```bash title="Run without installing"
    uv tool run terminaltexteffects -h
    ```

=== "Nix (flakes)"

    ```bash title="Create a shell with TTE"
    nix shell github:ChrisBuilds/terminaltexteffects
    ```

    ```bash title="Run directly"
    echo 'terminaltexteffects is awesome' | nix run github:ChrisBuilds/terminaltexteffects -- beams
    ```

    These commands use development `main` and require the `nix-command` and `flakes` features. See the
    [README](https://github.com/ChrisBuilds/terminaltexteffects#installation) for pinning a release, flake inputs,
    and classic Nix.

=== "pip"

    ```bash
    pip install terminaltexteffects
    ```

    Without pipx, run TTE through the Python module when the `tte` command is not on your `PATH`:

    ```bash title="ls redirection"
    ls -latr | python3 -m terminaltexteffects
    ```

Optionally, enable [shell completion](./appguide.md#shell-completion) for effect names and options.

[Application Usage](./appguide.md){ .md-button }

## Library

When installed as a library, TerminalTextEffects can be imported to produce animations in your Python applications.

=== "pip"

    ```bash
    pip install terminaltexteffects
    ```

=== "uv"

    ```bash
    uv add terminaltexteffects
    ```

[Library Usage](./libguide.md){ .md-button }

## Installing Development `main`

This documentation follows development `main`, so some documented features are not yet in the published release.
To try them, install from the repository:

```bash
pipx install git+https://github.com/ChrisBuilds/terminaltexteffects.git
```

Development `main` can change at any time. Use the published release for stable behavior.
