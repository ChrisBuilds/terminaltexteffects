# Continuous integration

The development process is defined in [CONTRIBUTING.md](../CONTRIBUTING.md).
Focused verification runs locally; broad default suites run here on PRs and pushes to `main`.
Broad local runs are reserved for diagnosing failures or explicit requests.

`workflows/ci.yml` runs on pull requests (including drafts), pushes to `main`, and manual dispatch.
Pushes to an issue branch with an open PR trigger one PR run, not a duplicate push run.
For a branch without a PR, open a draft PR or manually dispatch CI. Tag pushes do not trigger CI;
manual dispatch always requests full validation. Local QA hooks are optional; no private runner is needed.

[Dependency update automation](DEPENDENCIES.md) groups routine Dependabot PRs. They retain
the same required checks and need a tracking issue and changelog decision before merge.

The matrix runs the default pytest suite on the latest patch releases of Python 3.9 through 3.14
using Ubuntu 24.04. The package minimum is Python 3.9.2; 3.9.0 and 3.9.1 are unsupported.
Documentation/release/hooks require Python 3.10+; CI already runs those on 3.14.
The native 3.9 test job installs only the test group. Modern jobs use patched pytest;
the 3.9 pytest temporary-directory advisory remains under separate remediation
(see [dependency policy](DEPENDENCIES.md#runtime-and-tooling-python-support)).
It uses locked test dependencies, installs a non-editable package, and checks package import
and CLI startup from outside the checkout. Bash and Zsh completion behavior is covered by
the tests, and a separate job checks that the committed completion scripts are current.
Manual, visual, and exhaustive effect-argument tests remain outside this workflow.
Pytest reports the 20 slowest test durations to guide future test optimization.
Existing pytest steps also write seven-day JUnit artifacts and small reproduction
metadata; a 120-second per-test timer dumps tracebacks without stopping the test.
See [test-failure diagnostics](TEST_DIAGNOSTICS.md) for artifact names, limitations,
and exact-revision focused reproduction. Missing or cancelled reports are not passes.
Only the Linux Python 3.14 job instruments this same run for [line and branch coverage](COVERAGE.md),
with a summary and short-lived report artifacts. No percentage threshold is enforced.

Focused native-platform jobs run on `windows-2025` and `macos-15`, each with Python 3.14.
They use locked non-editable installations, check both CLI entry points from outside the
checkout with seeded piped input and cursor restoration, and run terminal/ANSI/Unicode,
configuration, and selected platform-independent CLI regressions. PowerShell 7 integration
tests exercise native completion for both CLI names, options/values, quoting, file paths,
and prototype isolation. PowerShell must be available in these jobs; absence fails rather
than silently skipping integration checks. UTF-8 mode is explicit.
Bash is used only to orchestrate commands on Windows; the Python interpreter and console
entry points are native Windows executables. No WSL or private CI server is required.
These checks do not verify how a human terminal displays the animation; visual QA remains
part of the release checklist. Full effect-configuration coverage stays in the Linux matrix.

New job names are `Windows / Python 3.14` and `macOS / Python 3.14`. They run on code-bearing
changes and manual dispatch, with lightweight success steps for documentation-only PRs.
Both names are required in main branch protection alongside the original eight checks.

The quality job classifies the committed diff, including deleted files and both sides of renames.
Only Markdown prose in the root, documentation, changelog, and non-workflow GitHub directories,
plus documentation images, may bypass the matrix and completion generation. Unknown files,
Python source, tests, dependencies, packaging, and CI configuration require the full matrix.
The existing strict MkDocs build runs once in Code quality when changes touch recognized
prose, anything under `docs/` or `overrides/`, the runtime `terminaltexteffects/` package,
`mkdocs.yml`, `pyproject.toml`, `uv.lock`, or the CI/documentation deployment workflows.
Source-only and dependency-only changes therefore validate API rendering and documentation
integration without depending on an accompanying Markdown changelog fragment. Deletions
and both sides of renames count as inputs. Tests-only and unrelated tool/workflow changes
do not independently request docs; manual runs still request full validation.
Classification regression tests run in Code quality on every run, including documentation-only
changes. The matrix does not repeat the docs build; the separate post-merge deployment
still rebuilds the exact tested main commit. All changes retain changelog validation.
Documentation-only matrix and completion jobs perform a short success step so all ten required check names remain present; the whole workflow is never path-filtered.

New pushes cancel obsolete runs for the same branch or pull request. Each Python version
reports separately, and a failure on one version does not cancel the other matrix jobs.

Branch protection for `main` requires these checks before merging:

- `Python 3.9`
- `Python 3.10`
- `Python 3.11`
- `Python 3.12`
- `Python 3.13`
- `Python 3.14`
- `Shell completions`
- `Code quality`
- `Windows / Python 3.14`
- `macOS / Python 3.14`

GitHub branch protection requires PRs, the checks above, up-to-date PR branches
(`required_status_checks.strict=true`), resolved conversations,
and enforcement for administrators. Mandatory external approvals remain at zero for solo
maintenance; the maintainer still reviews and decides when to merge. Use squash merging
and delete merged issue branches. Workflow configuration and templates alone do not enforce
these rules; required checks and branch protection enforce them at merge time.

Strict status checking requires the PR branch to include current `main`. When main advances,
refresh the next PR intended for merge, review any conflict resolutions, push, and wait for
all required checks on the new revision. If main advances again, refresh and recheck.
Retarget stacked PRs to main after their prerequisites merge, then integrate the squash
merge and revalidate. Re-running an old revision or bypassing protection is not a substitute.
See [branch refresh instructions](../CONTRIBUTING.md#refresh-a-pr-before-merging).

This adds no job or required check name. It can require another ordinary CI cycle for an
outdated PR. Refresh only the next PR to merge to avoid repeatedly testing every waiting
branch. Existing diff classification and obsolete-run cancellation continue to control cost.
GitHub settings enforce this requirement; editing these documents does not change it.

GitHub Actions owns the supported-version matrix. Local verification uses the repository
venv commands in [CONTRIBUTING.md](../CONTRIBUTING.md).
When changing the minimum supported Python version or adding a supported version, update
the workflow matrix alongside `pyproject.toml` and its Ruff/Pyright version targets as appropriate.

`Code quality` runs once on Python 3.14 with locked development dependencies. Ruff checks
formatting and lint; Pyright checks types targeting Python 3.9. These checks are read-only
and cover every tracked Python file and stub, including unchanged callers, tests, tools, and
archived experiments. Ignored and untracked local prototypes stay outside CI's inventory.
Documentation-only changes still run quality checks. Reproduce them locally with
`./.venv/bin/python tools/check_quality.py --all`; changed-file checks remain available with
`--base origin/main` for focused development.

On PR events, Code quality first runs the pinned [dependency vulnerability review](DEPENDENCIES.md#dependency-vulnerability-gate)
for newly introduced high/critical findings across runtime/development/unknown scopes, then
checks reported uv changes against both universal locks. Missing dependency pairs fail;
unchanged alerts remain Dependabot's responsibility. Push/manual runs omit the differential
review but still run offline guard regressions. No new required job or write permission is added.

For code-bearing changes, the quality job also validates `.pre-commit-config.yaml` and runs the
focused hook regression tests.
Real hook integration uses the locked development environment here; matrix jobs run the hook dispatcher
unit tests and skip integration cases when development-only tools are absent. Local hooks use the same
Ruff and Pyright settings, run on staged files, and do not replace CI enforcement. See the installation
and staging guidance in [CONTRIBUTING.md](../CONTRIBUTING.md).

Code quality also runs the read-only shipped-effect inventory and its focused fixtures on
every run, using locked development tools. `tools/check_effect_inventory.py` connects shipped
`effect_*.py` modules to built-in command registration, permanent command-named test files
with test definitions, nonempty documentation pages, and structural MkDocs navigation entries.
It disables user/development discovery and rejects stray shipped prototypes or command/config
name mismatches. This structural gate does not prove test quality or visual correctness.
The existing Shell completions job remains responsible for generated-resource freshness;
completion generation is not duplicated in the inventory check. Follow the
[effect promotion checklist](../dev_effects/README.md#promotion-checklist).

All ten required checks are restricted to results from GitHub Actions.

The same job validates changelog fragments, the generated Unreleased preview, and the branch's
changelog decision for PRs and pushes to `main`. Manual runs validate fragments and
preview freshness without requiring a new changelog decision. Add a user-facing fragment or an
explicit `.skip.md` reason. Release branches
are accepted when they consume fragments into a new dated section of the canonical changelog.
Preview edits alone do not bypass the fragment requirement. All checks are read-only.


## Release validation

Code-bearing changes also run `tools/check_artifacts.py` once in Code quality: wheel/source
builds, source-rebuilt wheel validation, metadata/README checks, prototype exclusion, and
clean installations outside the checkout. Documentation-only changes skip this step.

Routine CI is a release prerequisite, not publication approval. The
[release runbook](../RELEASING.md) and [release checklist](ISSUE_TEMPLATE/release.md) add
exhaustive pre-release configuration tests, human visual/terminal QA, relevant performance
evidence, final-commit validation, and exact-artifact approval. Exhaustive runs are dedicated
pre-release work; the existing CI workflow runs the default pairwise suite even on manual dispatch.
Publication remains manual and requires explicit maintainer authorization. Future publishing
automation is a separate improvement.

## Documentation publication

Successful main push CI triggers the separate [documentation deployment workflow](DOCUMENTATION.md).
It strictly rebuilds the exact tested current-main commit and publishes through GitHub Pages.
PRs never publish; the site identifies itself as development documentation. See the linked
guide for the one-time Pages cutover, environment settings, retry, and recovery.

## Workflow linting

Every Code quality run checks all existing tracked `.github/workflows/*.yml` and `.yaml`
files with actionlint **1.7.12**, including documentation-only PRs. CI downloads the exact
Linux release archive, verifies its committed SHA-256, and runs
`tools/check_workflows.py`. Update the version constant, download URL, and checksum together
when upgrading; review the upstream release and rerun the fixtures. Dependabot does not
manage this binary pin.

Actionlint validates workflow structure, expressions/contexts, dependencies, runner labels,
and action usage. ShellCheck is required explicitly for Bash/sh `run` steps. CI uses the
Ubuntu hosted image's ShellCheck installation and prints its version; its version is not
pinned by this repository. Missing tools and a different actionlint version fail clearly.
Pyflakes integration is explicitly disabled so results do not vary with incidental PATH
contents. This does not lint PowerShell, Python heredocs, or prove a remote action works;
existing Python tests/types and native-platform checks remain necessary.

For local checks, install the official [actionlint 1.7.12 platform release](https://github.com/rhysd/actionlint/releases/tag/v1.7.12)
(verify its published checksum) and [ShellCheck](https://github.com/koalaman/shellcheck#installing)
on PATH. Alternatively set `TTE_ACTIONLINT` and `TTE_SHELLCHECK` to their executable paths.
Then run:

```sh
./.venv/bin/python tools/check_workflows.py
TTE_REQUIRE_ACTIONLINT=1 ./.venv/bin/pytest -q tests/test_workflow_lint.py
```

The helper is read-only, downloads nothing, and accepts explicit workflow paths for focused
checks. Its default inventory excludes untracked scratch workflows and deleted files.
Real-tool fixtures prove rejection of invalid expressions, nonexistent job dependencies,
and unquoted shell values. Code quality requires them; matrix jobs skip these integration
fixtures when external tools are absent and still run dispatcher/selection tests.

The optional `workflows` pre-commit hook uses the same helper and has only the `manual`
stage. It does not run during ordinary commits, so existing commit hooks need no new tools.
Invoke it after installing the tools:

```sh
./.venv/bin/pre-commit run workflows --hook-stage manual --files .github/workflows/ci.yml
```

Pre-commit handles staged/unstaged isolation when invoked on the index; the linter never
modifies files or staging. No extra required job or duplicate matrix run is added.

## Informational coverage comparisons

`tools/report_coverage.py` replaces the inline coverage summary in the existing Linux/Python
3.14 run. It publishes separate line/branch percentage-point changes against successful main
CI at the exact PR base SHA, plus untested added/modified executable runtime lines. Baselines
require matching collection/selection configuration (including the CI workflow fingerprint),
profile/tool versions and successful
main provenance. Unavailable or incompatible baselines show a reason without a delta;
coverage decreases do not fail CI. Current collection errors and test failures still fail.

The matrix job has read-only `contents` and `actions` permissions; only its reporting step
receives the built-in token. It reads two JSON archive members, without extracting/executing
artifacts or posting comments. Requests are individually bounded at 20 seconds. Python 3.14
checkout fetches two commits of depth to read the tested merge parents; a missing exact
base diff is reported as unavailable. Other matrix checkouts retain depth one. No new suite,
job, service or dependency is added. Focused reporting regressions run in Code quality.

`context.json` accompanies existing artifacts for 14 days. Older artifacts without this
metadata cannot be compared; successful main CI after deployment establishes the first
compatible baseline. See [coverage reporting](COVERAGE.md) for selection, missing-baseline
behavior, changed-line detail and interpretation.

## Portable hooks and text hygiene

After `uv sync --locked --group dev`, install optional commit hooks with
`uv run --no-sync --offline python -m pre_commit install --allow-missing-config`.
The same entries work on POSIX and native Windows without hard-coded venv binary
paths. Keep uv on PATH when committing in terminals or editors. No-sync/offline
execution uses already-installed tools without lock updates or dependency installation;
it does not verify that an old environment is current. Sync explicitly after branch changes.

The read-only `hygiene` hook rejects trailing spaces/tabs and standalone Git conflict
markers in selected text files. Markdown hard breaks with two or more trailing spaces
are permitted; whitespace-only lines and trailing tabs are rejected. Binary files,
symlinks and deletions are excluded. Entire selected files are checked, so existing
issues in a touched file need correction. Local staging isolation is provided by
pre-commit; use its selected-file interface instead of directly calling the dispatcher
when you need index-only validation. The changelog hook retains its index snapshot.

Code quality repeats hygiene on changed files from the committed merge-base diff,
including documentation-only PRs. It does not scan unrelated historical files; a manual
run on unchanged main has no changed files. Reproduce after committing with:

```sh
./.venv/bin/python tools/run_hook.py hygiene --base origin/main
```

The existing Windows job syncs only `test` + `hooks` for real pre-commit integration.
The new group reuses locked Ruff, Pyright, and pre-commit without adding packages or
changing versions; full `dev` still includes those tools. Regression tests cover real
fix/restage behavior, overlapping unstaged changes, read-only hygiene, paths with spaces,
and changelog snapshots. `TTE_REQUIRE_HOOK_INTEGRATION=1` makes missing integration
tools a failure in Code quality and Windows rather than silently skipping these tests.

## Executable documentation examples

Code quality runs `tests/test_documented_examples.py` on every run, including
documentation-only PRs. The same small suite also runs in the ordinary Linux Python matrix.
It reads two explicitly marked standalone code blocks directly from `docs/libguide.md`
(`library-wipe`, Python) and `docs/appguide.md` (`cli-wipe`, Bash). There is no separate
copy of their implementation in tests and no execution of arbitrary other docs blocks.

The Python example consumes an effect iterator and checks its final frame. The CLI example
uses literal piped input and global/effect options, checking final text and cursor restoration.
Both run in subprocesses outside the checkout with empty user configuration, explicit UTF-8,
a fixed small canvas, zero playback delay, and a 10-second timeout each. The Python example
uses this environment's interpreter; the CLI check verifies the selected `tte` comes from
that environment. Bash profiles/startup overrides and prototype discovery are excluded.
Bash is mandatory in Code quality; local runs without Bash may skip only the POSIX CLI case.

Run locally after syncing locked tools:

```sh
TTE_REQUIRE_DOC_EXAMPLES=1 ./.venv/bin/pytest -q tests/test_documented_examples.py
```

Keep each marker unique in its page and directly before a flush-left `python` or `bash`
fence with a closing fence. Missing/duplicate markers and incorrect/unterminated fences
fail clearly. When editing a selected example, run this check and update semantic assertions
if its intended result changes. Follow normal review for changed public behavior.

Add selections deliberately: keep them short, standalone, deterministic in their assertions,
free of network/installation/credential requirements, and with explicit timeouts and meaningful
results. Examples needing files should supply temporary fixtures. Do not blanket-execute
installation commands, interactive snippets, demonstrations, or every Markdown fence.
These checks supplement strict MkDocs/link validation; they do not verify visual fidelity,
all examples, or every terminal/shell. Human visual and release QA remain necessary.

## Scheduled source and workflow security analysis

[CodeQL security scanning](CODEQL.md) is a separate weekly/manual main-only workflow
for Python and GitHub Actions. Its initial default-query results are reviewed in Security
-> Code scanning; it is outside required PR CI and branch protection. Only its analysis
job has security-events upload permission. There is no extra test suite or publishing step.
PR Code quality still lints the workflow configuration. Activation, initial hosted scan
verification, triage and dismissal rules are described in the linked guide.

## Manual exhaustive release validation

`exhaustive.yml` runs only on manual dispatch from main, using a required immutable
candidate SHA. It runs Linux/Python 3.14 exhaustive automated tests, records the verified
revision and reproduction metadata, and retains log/JUnit/exit-status evidence for 30 days.
It has no push/PR trigger or publishing permissions and is not an ordinary required PR
check. See [EXHAUSTIVE_VALIDATION.md](EXHAUSTIVE_VALIDATION.md) and the release runbook.

## Post-merge verification

Follow [POST_MERGE.md](POST_MERGE.md) after an authorized merge to identify the exact
main push run, inspect actual scope, verify live documentation and record evidence. It
explains superseded runs, justified infrastructure reruns and scoped follow-up fixes.
