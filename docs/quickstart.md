# Quickstart

## Application Quickstart

When used as a system application, TerminalTextEffects will produce animations on text passed via stdin. Often, passing data to TTE occurs via pipes or redirection.

### Application Invocation Examples

```bash title="Piping directory listing output through TTE"
ls -latr | tte slide
```

```bash title="Redirecting a file through TTE"
tte slide < your_file
```

### Application Configuration

TTE has many global terminal configuration options as well as effect-specific configuration options available via command-line arguments.

Terminal configuration options should be specified prior to providing the effect name. The basic format is as follows:

```bash title="TTE usage syntax"
tte [global_options] <effect_name> [effect_options]
```

Using the `-h` argument in place of the global_options or effect_options will produce either the global or effect help output, respectively.

The example below will pass the output of the `ls` command to TTE with the following options:

* Global options:
    - Text will be wrapped if wider than the terminal.
    - Tabs will be replaced with 4 spaces.

* Effect options:
    - Use the slide effect.
    - Merge the groups.
    - Set movement-speed to 2.
    - Group by column.

```bash title="TTE argument specification example"
ls | tte --wrap-text --tab-width 4 slide --merge --movement-speed 2 --grouping column
```