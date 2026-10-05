# Development effects

Keep unfinished effects here, outside the shipped package. Issue-branch prototypes may be
committed; `effect_dev.py` remains ignored for personal scratch work. No Python files in this
directory are included in wheels or source distributions.

From the repository root, run the development CLI:

```sh
printf 'Hello' | ./.venv/bin/python -m tools.dev dev
```

Use your effect's command name in place of `dev`. Modules use the normal
`get_effect_resources()` interface and absolute imports from `terminaltexteffects`.
This loader supports flat modules; avoid relative sibling imports.

Parser-based tools, including the benchmark tool, use the same discovery:

```sh
TTE_DEV_EFFECTS_DIR="$PWD/dev_effects" ./.venv/bin/python tools/perf/benchmark_effects.py --effect dev
```

Run focused prototype tests and QA on the issue branch. Development effects are loaded only
when explicitly selected through the launcher or `TTE_DEV_EFFECTS_DIR`. Release completion
generation and built-in-only parser calls exclude them even when that setting exists.

To promote an effect, move its module into `terminaltexteffects/effects/` in a reviewed PR,
add permanent tests and documentation, regenerate completions, and add a changelog fragment.
Never place scratch modules in the shipped effects directory. Release validation injects a
prototype into a temporary source copy and requires its exclusion from all distribution formats.
