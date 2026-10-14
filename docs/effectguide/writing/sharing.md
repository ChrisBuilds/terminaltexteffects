# Sharing your effect

A community effect is a single `.py` file that other people copy into their community effects directory. This page
covers what to publish alongside that file and where to share it.

## Before you share

- Run your effect's tests and try it on your own terminal with a few inputs, including colored input if your effect
  supports it. [Step 7: Harden](../tutorial/07-harden.md) shows how.
- Check that it uses only public APIs: names exported by `terminaltexteffects` and the public modules under
  `terminaltexteffects.engine` and `terminaltexteffects.utils`. Anything starting with an underscore can change in any
  release.
- Pick a command name no built-in effect uses, and a file name that isn't the name of a standard-library or installed
  module (see [Discovery and loading](../engine/loading.md#community-effects)).
- Keep the effect in one file. If it needs another package, say so; users install it into the same Python environment
  as TTE.

## What to publish

Put the module in a public repository or Gist, with:

| Item | Why |
| --- | --- |
| A short demo | People decide from the animation. A screen recording, or an [asciinema](https://asciinema.org) recording converted with [agg](https://github.com/asciinema/agg), works. |
| The supported TTE version | Engine APIs can change between releases. State the version you tested with, such as "TTE 0.16.0". |
| Install and run steps | Where to put the file, any dependencies, and an example command. |
| The options | `tte <effect> -h` output, or a list of options and their defaults. |
| How it handles input colors | Which `--existing-color-handling` settings it supports, and what `dynamic` does. |
| A license | So people know how they may use and change it. |
| Maintenance status | Whether you plan to update it for new TTE releases. |

The install steps can be as short as this, with your file and command names:

```bash
mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/terminaltexteffects/effects"
cp myspray.py "${XDG_CONFIG_HOME:-$HOME/.config}/terminaltexteffects/effects/"
tte myspray -h
```

## Where to share it

Post it in the [TTE Effect Show and Tell](https://github.com/ChrisBuilds/terminaltexteffects/discussions/categories/tte-effect-show-and-tell)
discussion category with the items above. A post there is a community listing: the effect stays hosted and
maintained by you, and isn't bundled with TTE or endorsed by its maintainers.

## When TTE changes

The [changelog](../../changelog.md) lists breaking engine changes in each release. When a new TTE version comes out,
run your tests against it, fix what broke, and update the supported version you state.

## Proposing a built-in effect

To propose your effect for TTE itself, open an issue describing it, with a demo. Built-in effects go through review
and the [promotion checklist](https://github.com/ChrisBuilds/terminaltexteffects/blob/main/dev_effects/README.md#promotion-checklist),
which adds tests, documentation, and shell completion. Read [CONTRIBUTING.md](https://github.com/ChrisBuilds/terminaltexteffects/blob/main/CONTRIBUTING.md)
first.
