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

Optional pre-commit hooks run whitespace/conflict-marker checks, Ruff lint fixes and formatting,
Pyright, and changelog validation on staged files:

```sh
uv run --no-sync --offline python -m pre_commit install --allow-missing-config
```

Hooks are a convenience; CI is the enforced gate. If a hook rewrites a file, review and restage it.

To diagnose a Python 3.9 problem, use a separate environment so the main one stays intact:

```sh
UV_PROJECT_ENVIRONMENT=/absolute/path/to/tte-python39 uv sync --locked --no-default-groups --group test --python 3.9
```

## Workflow

Work follows **issue → branch → draft PR → maintainer squash merge**. Keep one coherent change per
issue and PR; open separate issues for unrelated findings.

1. **Issue.** Describe the problem, scope, and acceptance criteria. Verify reported bugs before
   fixing them. Changes to effect options, defaults, or visual behavior need agreement in the
   issue before implementation. Issue metadata:
   - assignee `ChrisBuilds`;
   - exactly one type label: `bug`, `enhancement`, `documentation`, or `maintenance`;
   - one or more area labels: `effects`, `engine`, `cli`, `ci`, or `release`;
   - the release milestone if the work is scheduled for a release, otherwise none.

   Use `blocked` or `needs-decision` only for a real impediment, with an explanation.
2. **Branch.** Start from current `main` and name it `<type>/<issue-number>-<short-description>`,
   for example `fix/123-wide-chars` or `docs/125-api-examples`. Never commit to `main` directly.
3. **Change.** Include related tests, docs, regenerated completions, and a changelog fragment in
   the same branch. Keep personal notes out of commits.
4. **Draft PR.** Use the PR template, include `Closes #<issue>`, describe the resulting behavior
   and your validation, and list known limitations. Assign `ChrisBuilds` and copy the issue's labels
   and milestone. Open it early if you want CI feedback; CI runs on draft PRs.
5. **Ready.** When local checks and CI pass, mark the PR ready. This automatically requests a Codex
   review. Address or answer each finding in its thread, then resolve the conversation.
6. **Merge.** Only the maintainer merges, using squash merge. GitHub deletes the remote branch.

## Local checks

Run focused checks for what you changed; the full matrix runs in CI.

```sh
./.venv/bin/ruff format <files>
./.venv/bin/pytest -n auto tests/effects_tests/test_<effect>.py      # or a single ::test node
./.venv/bin/ruff check <files>
./.venv/bin/pyright --pythonpath ./.venv/bin/python <files>
```

`uv run --no-sync --offline python -m tools.qa --dry-run` shows which checks apply to your branch
changes; add `--test <file-or-node>` to run them with focused tests. To reproduce CI's whole-project
quality check, run `./.venv/bin/python tools/check_quality.py --all`.

Situational checks:

- **Documentation-only changes:** no pytest/Ruff/Pyright needed; check formatting and links, and run
  `./.venv/bin/mkdocs build --strict` for `docs/` changes.
- **Canonical examples** in `docs/libguide.md` or `docs/appguide.md` (marked blocks):
  `./.venv/bin/pytest -q tests/test_documented_examples.py`.
- **CLI option changes:** `./.venv/bin/python tools/generate_shell_completions.py`, then `--check`.
- **Workflow changes:** `./.venv/bin/python tools/check_workflows.py` (needs actionlint 1.7.12 and
  ShellCheck on `PATH`, or `TTE_ACTIONLINT`/`TTE_SHELLCHECK`).
- **Nix packaging changes:** `bash tools/check_nix.sh` (needs Nix with flakes). Refresh nixpkgs
  deliberately with `nix flake update nixpkgs`.
- **Visual and manual tests** are excluded by default; run them when a human needs to look:
  `./.venv/bin/pytest -s -m visual tests/test_effects.py -k <Effect>`.
- **Exhaustive effect arguments** (`--exhaustive-effect-args`) are for release validation only;
  normal runs use pairwise coverage.
- **Performance claims** need before/after measurements with fixed seeds; see
  [docs/performance.md](docs/performance.md).

## Changelog

Every PR adds a fragment in `changelog.d/` named after its issue, then refreshes the generated
Unreleased preview:

```sh
./.venv/bin/towncrier create --content "Describe the user-visible change." 123.fixed.md
./.venv/bin/python tools/generate_changelog.py
```

User-facing changes use a category (`breaking`, `added`, `changed`, `deprecated`, `removed`, `fixed`,
`security`). Internal changes, and fixes to bugs introduced since the last release, use
`123.skip.md` containing a one-line reason. Never edit the generated preview by hand; regenerate it,
including when resolving merge conflicts. See [changelog.d/README.md](changelog.d/README.md).

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

## CI

`.github/workflows/ci.yml` runs on PRs (including drafts), pushes to `main`, and manual dispatch.

| Job | Checks |
| --- | --- |
| Code quality | Ruff, Pyright on all tracked Python files; text hygiene on changed files; changelog fragments, preview, and changelog decision; dependency review on PRs; actionlint; effect inventory; documented examples; strict docs build when docs, source, or dependencies change; wheel/sdist build and install checks |
| Python 3.9 – 3.14 | Default test suite on Linux; 3.14 also reports informational coverage |
| Windows / macOS, Python 3.14 | Native CLI, terminal, config, and PowerShell completion tests |
| Shell completions | Committed completion scripts are current |
| Nix / Linux, Nix / macOS | Flake and classic package builds and CLI smoke tests (not required) |

Changes containing only Markdown prose and images skip the test, completion, and Nix jobs, and those
jobs report success so the required check names still appear.

Branch protection on `main` requires the ten checks above other than Nix. It also requires PRs,
up-to-date branches, and resolved conversations, applies to admins, and needs no approving reviews.
When `main` moves ahead of a PR you want to merge, update the branch:

```sh
git fetch origin && git merge origin/main
```

Do this only for the next PR to merge. Fix conflicts, regenerating the changelog preview rather than
choosing a side, and push so CI reruns.

**When CI fails,** open the first failing step. Test jobs upload JUnit results and `context.json`
(tested SHA, interpreter, tool versions) as `test-results-*` artifacts for seven days. Tests running
longer than 120 seconds dump a traceback. Reproduce narrowly at the tested revision, then fix on the
branch. Rerun a job only if there's evidence of a transient infrastructure failure.

**After merge,** a successful `main` CI run triggers `docs.yml`, which publishes the documentation
site from that commit; each page shows a banner linking the commit. GitHub notifies you of failures.
To redeploy after fixing a failure, run `gh workflow run docs.yml --ref main`. Delete the merged
local branch and any worktree you created for it.

## Dependencies and security

Dependabot opens grouped weekly PRs for `uv.lock` and GitHub Actions; security updates arrive
separately. Before merging a bot PR, create a tracking issue with the usual metadata, link it with
`Closes #<issue>`, and push a fragment (usually `.skip.md`) and refreshed preview to the bot branch.
Review major upgrades individually. Keep actions pinned to full commit SHAs.

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
