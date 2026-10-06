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

## Promotion checklist

Promote a finished effect through the normal issue -> branch -> draft PR -> review ->
maintainer merge process. Review these items in the PR; CI cannot approve artistic or
behavioral decisions:

- [ ] Record the effect's intended appearance and behavior, supported input, options, and
  defaults in the issue. Agree on options/defaults/visual changes before implementation.
- [ ] Move the finished `effect_<module>.py` into `terminaltexteffects/effects/` and remove
  the promoted prototype copy. Keep other unfinished experiments in `dev_effects/`.
- [ ] Verify `get_effect_resources()` and config parser metadata use the same unique command.
  Check normal `tte <command> --help` discovery without `TTE_DEV_EFFECTS_DIR` or plugins.
- [ ] Add permanent `tests/effects_tests/test_<command>.py` behavior/configuration tests.
  Cover meaningful edge cases (for example empty/small/sparse input, termination, seeded
  behavior, and supported existing-color handling). Test presence alone is insufficient.
- [ ] Add `docs/effects/<command>.md` with accurate CLI and Python examples, options/defaults,
  and supported limitations; add the page to `mkdocs.yml` navigation. Provide a demo where
  useful or explain why it is deferred; keep any referenced demo assets valid.
- [ ] Regenerate Bash, Zsh, and PowerShell completions using
  `./.venv/bin/python tools/generate_shell_completions.py`, then run its `--check` mode.
- [ ] Add an issue-numbered user-facing fragment (normally `.added.md`) and regenerate the
  Unreleased preview. A newly shipped effect is not an internal-only skip.
- [ ] Run focused effect tests, formatting, lint, and Pyright, plus
  `./.venv/bin/python tools/check_effect_inventory.py` and a strict docs build.
- [ ] Verify release artifacts include the promoted module while other development effects
  remain excluded. CI's artifact check protects the distribution boundary; inspect its result.
- [ ] Record human visual/terminal QA: appearance/pacing, representative layouts and Unicode,
  supported color modes, interruption/cursor restoration, and relevant terminal platforms.
  Record limitations or reasoned N/A cases. Measure performance changes with controlled
  before/after inputs/seeds and explain any intended output changes.
- [ ] Address review feedback and require latest CI before the maintainer decides to merge.
  Publication remains a separate release process; promotion approval does not publish.

## Automated inventory gate

Code quality runs `tools/check_effect_inventory.py` against the shipped package and checks:

- Every `effect_*.py` module appears in built-in registration, and registered effects have
  shipped modules. Development/plugin discovery is disabled. A stray `effect_dev.py` fails.
- CLI subcommands agree with effect-resource command names.
- Each command has a nonempty `docs/effects/<command>.md`, a page entry under MkDocs `nav`,
  and `tests/effects_tests/test_<command>.py` defining a top-level test or Test-class method.

Tests/docs are named by command; the module suffix may differ (for example
`effect_random_sequence.py` registers `randomsequence`). Navigation is parsed as YAML,
not searched as text. The helper is read-only and uses the locked development environment.
The existing required Shell completions check verifies generated resources separately.

This gate checks structure, not test assertions, actual test collection/execution, correctness
of prose, demo quality, or visual fidelity. Focused tests, broad CI, strict docs, artifact
validation, and human review remain required. Development prototypes need not satisfy this
shipped-effect inventory until promoted.
