# Contributing

TerminalTextEffects (TTE) is a small project with one maintainer, `ChrisBuilds`. This file is the
single description of how changes are developed, checked, merged, and released. Outside contributors
are welcome: open an issue or a PR, and the maintainer will take care of labels, milestones, and
anything else in this file you missed.

Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md). For usage problems,
see [SUPPORT.md](SUPPORT.md).

## Setup

TTE runs on Python 3.9.2+. Development tools (docs, hooks, release tooling) need Python 3.10+;
use 3.14:

```sh
uv sync --locked --group dev --python 3.14
```

Use the tools in `./.venv/bin`. Re-run the sync after switching branches or changing `uv.lock`.

Install the pre-commit hooks once per clone:

```sh
./.venv/bin/pre-commit install
```

They run trailing-whitespace and conflict-marker checks, Ruff lint and formatting, Pyright,
actionlint, ShellCheck, and changelog validation on the files you commit, using the tools in
`uv.lock`. CI runs the same hooks on every file, so a clean local run means those checks pass
in CI. If a hook rewrites a file, review and restage it.

To diagnose a Python 3.9 problem, use a separate environment so the main one stays intact:

```sh
UV_PROJECT_ENVIRONMENT=/absolute/path/to/tte-python39 uv sync --locked --no-default-groups --group test --python 3.9
```

## Workflow

Work follows **issue → branch → draft PR → maintainer squash merge**. Keep one coherent change per
PR; open separate issues for unrelated findings.

1. **Issue.** Open an issue for bugs, features, and anything needing discussion or acceptance
   criteria. Small, self-explanatory changes (typos, docs fixes, routine maintenance) can go straight
   to a PR. Verify reported bugs before fixing them. Changes to effect options, defaults, or visual
   behavior need agreement in the issue before implementation. Issue metadata:
   - assignee `ChrisBuilds`;
   - exactly one type label: `bug`, `enhancement`, `documentation`, or `maintenance`;
   - one or more area labels: `effects`, `engine`, `cli`, `ci`, or `release`;
   - the release milestone if the work is scheduled for a release, otherwise none.

   Use `blocked` or `needs-decision` only for a real impediment, with an explanation.
2. **Branch.** Start from current `main` and name it `<type>/<issue-number>-<short-description>`
   (or `<type>/<short-description>` without an issue), for example `fix/123-wide-chars` or
   `docs/api-examples`. Never commit to `main` directly.
3. **Change.** Include related tests, docs, regenerated completions, and a changelog fragment for
   user-facing changes in the same branch. Keep personal notes out of commits.
4. **Draft PR.** Use the PR template, include `Closes #<issue>` when there is one, describe the
   resulting behavior and your validation, and list known limitations. Assign `ChrisBuilds` and use
   the same labels and milestone rules as issues; add `no-changelog` when no fragment is needed.
   Open it early if you want CI feedback; CI runs on draft PRs.
5. **Ready.** When local checks and CI pass, mark the PR ready. This automatically requests a Codex
   review. Address or answer each finding in its thread, then resolve the conversation.
6. **Merge.** Only the maintainer merges, using squash merge. GitHub deletes the remote branch.

## Local checks

Run focused checks for what you changed; the full matrix runs in CI.

```sh
./.venv/bin/pytest -n auto tests/effects_tests/test_<effect>.py   # or a single ::test node
./.venv/bin/pre-commit run --files <changed files>                 # lint, format, types, etc.
```

Committing runs the hooks automatically; `pre-commit run --all-files` reproduces CI's quality checks.

Situational checks:

- **Documentation-only changes:** no pytest/Ruff/Pyright needed; check formatting and links, and run
  `./.venv/bin/mkdocs build --strict` for `docs/` changes.
- **Canonical examples** in `docs/libguide.md` or `docs/appguide.md` (marked blocks):
  `./.venv/bin/pytest -q tests/test_documented_examples.py`.
- **CLI option or help changes:** `./.venv/bin/python tools/generate_shell_completions.py` and
  `./.venv/bin/python tools/generate_showroom.py`, then rerun each with `--check`.
- **Nix packaging changes:** `bash tools/check_nix.sh` (needs Nix with flakes). Refresh nixpkgs
  deliberately with `nix flake update nixpkgs`.
- **Visual and manual tests** are excluded by default; run them when a human needs to look:
  `./.venv/bin/pytest -s -m visual tests/test_effects.py -k <Effect>`.
- **Exhaustive effect arguments** (`--exhaustive-effect-args`) are for release validation only;
  normal runs use pairwise coverage.
- **Performance claims** need before/after measurements with fixed seeds; see
  [docs/performance.md](docs/performance.md).

## Changelog

User-facing changes add a fragment in `changelog.d/` named after the issue, or the PR when there is
no issue:

```sh
./.venv/bin/towncrier create --content "Describe the user-visible change." 123.fixed.md
./.venv/bin/python tools/changelog.py --preview
```

Categories are `breaking`, `added`, `changed`, `deprecated`, `removed`, `fixed`, and `security`.
Internal changes, and fixes to bugs introduced since the last release, need no fragment: apply the
`no-changelog` label to the PR. CI fails a PR that has neither; if you add the label afterwards, re-run
the failed jobs. Pending notes appear under Unreleased
on the documentation site; `CHANGELOG.md` gains them only at release. See
[changelog.d/README.md](changelog.d/README.md).

## Effects

Develop unfinished effects in the repository-root `dev_effects/` directory, never in
`terminaltexteffects/effects/`. Run one with `./.venv/bin/python -m tools.dev <effect>`, or set
`TTE_DEV_EFFECTS_DIR` for parser-based tools. Prototypes are excluded from builds. To ship an effect,
follow the [promotion checklist](dev_effects/README.md#promotion-checklist), which includes tests,
docs, completions, a changelog fragment, and recorded human visual QA.

Effects that won't be bundled can still be shared: TTE 0.15.0+ loads external effect modules
from `${XDG_CONFIG_HOME:-$HOME/.config}/terminaltexteffects/effects` (see the
[application guide](https://chrisbuilds.github.io/terminaltexteffects/appguide/#community-effects)),
and you can post them in
[TTE Effect Show and Tell](https://github.com/ChrisBuilds/terminaltexteffects/discussions/categories/tte-effect-show-and-tell).

### Demos

Effect demos in `docs/img/effects_demos/` and Effect Guide demos in `docs/img/effectguide/` are rendered locally
with `tools/render_demos.py` and committed; CI doesn't render them. Each folder's `demos.json` records a
fingerprint of every demo's seeded frames and render settings. `tests/test_demo_freshness.py` records each demo
again on Linux (Python 3.10+) and fails when a change to an effect, an example, an input file, the engine or the renderer would
change what a demo shows. Its message names the command that re-renders the demo, for example
`./.venv/bin/python tools/render_demos.py beams --out docs/img/effects_demos`; commit the new WebP and `demos.json`.

## CI

`.github/workflows/ci.yml` runs on PR pushes (including drafts), pushes to `main`, and
manual dispatch. Every run executes the full workflow:

| Job | Checks |
| --- | --- |
| Code quality | pre-commit hooks on all files; changelog fragments and decision; dependency review (PRs); effect inventory; documented examples; strict docs build; wheel/sdist build and install checks |
| Python 3.9 – 3.15 | Default test suite on Linux; 3.14 also reports coverage and untested changed lines (informational) |
| Windows / macOS, Python 3.14 | Native CLI, terminal, config, and PowerShell completion tests |
| Shell completions | Committed completion scripts are current |
| Nix / Linux, Nix / macOS | Flake and classic package builds and CLI smoke tests; on PRs only when `flake.*`, `default.nix`, `pyproject.toml`, `tools/check_nix.sh`, or `ci.yml` change |
| CI passed | Fails if any job above failed or was cancelled |

`.github/workflows/profile.yml` records Python 3.15 sampling profiles of the benchmark harness on
`main` and on manual dispatch; it is informational and not part of `CI passed`. See
[docs/performance.md](docs/performance.md#sampling-profiles).

Branch protection on `main` requires only `CI passed`, plus PRs and resolved conversations; it
applies to admins and needs no approving reviews. Branches don't have to be up to date with `main`
before merging; if a combination of merged PRs breaks `main`, its CI run catches it and the fix goes
in a follow-up PR.

**When CI fails,** open the first failing step. Test jobs upload JUnit results and `context.json`
(tested SHA, interpreter, tool versions) as `test-results-*` artifacts for seven days. Tests running
longer than 120 seconds dump a traceback. Reproduce narrowly at the tested revision, then fix on the
branch. Rerun a job only if there's evidence of a transient infrastructure failure.

**Random order and seeds.** pytest-randomly shuffles test order and reseeds `random` before every
test, using a new seed for each run. The seed is printed near the top of the test output as
`Using --randomly-seed=<seed>`. To reproduce a failure, run the failing test with that seed on the
same Python version:

```sh
./.venv/bin/pytest -p no:xdist --randomly-seed=<seed> <failing test id>
```

If the failure is order-dependent, run its module or the whole suite with the same seed. If a
seed-dependent failure appears on a PR that didn't cause it, open an issue that names the test and
the seed, then rerun the failed job; the rerun uses a new seed. Fix the failure in its own PR.

**After merge,** a successful `main` CI run triggers `docs.yml`, which publishes the documentation
site from that commit; each page shows a banner linking the commit. GitHub notifies you of failures.
To redeploy after fixing a failure, run `gh workflow run docs.yml --ref main`. Delete the merged
local branch and any worktree you created for it.

## Dependencies and security

Dependabot opens grouped monthly PRs for `uv.lock` and GitHub Actions, skipping releases younger than
a week (two weeks for major Python versions); security updates arrive
separately. They arrive labeled `maintenance`, `ci`, and `no-changelog`; review the release notes,
add a fragment and remove the label if users are affected, and merge once CI passes. Review major
upgrades individually. Keep actions pinned to full commit SHAs.

The dependency-review step fails a PR that introduces a high or critical advisory. Fix the dependency;
don't add allowlists, `continue-on-error`, or exclusions. The one known open alert, a pytest
advisory affecting only the Python 3.9 test environment
([#154](https://github.com/ChrisBuilds/terminaltexteffects/issues/154)), is resolved by dropping
Python 3.9 in 0.17.0 ([#184](https://github.com/ChrisBuilds/terminaltexteffects/issues/184)).
Leave it open until then.

CodeQL scans `main` (Python and Actions) weekly and on manual dispatch; results are in
**Security → Code scanning**. Fix real findings through a normal issue and PR. Dismissing alerts
needs the maintainer's decision. Keep exploit details out of public issues, PRs, and fragments.

## Releases

Follow [RELEASING.md](RELEASING.md). Release PRs use `Refs #<release-issue>` so the release issue
stays open until publication is verified. Merging a release PR does not authorize tagging or
publishing; that needs the maintainer's explicit approval.
