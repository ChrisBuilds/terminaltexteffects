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
It uses locked test dependencies, installs a non-editable package, and checks package import
and CLI startup from outside the checkout. Bash and Zsh completion behavior is covered by
the tests, and a separate job checks that the committed completion scripts are current.
Manual, visual, and exhaustive effect-argument tests remain outside this workflow.
Pytest reports the 20 slowest test durations to guide future test optimization.
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

GitHub branch protection requires PRs, the checks above, resolved conversations,
and enforcement for administrators. Mandatory external approvals remain at zero for solo
maintenance; the maintainer still reviews and decides when to merge. Use squash merging
and delete merged issue branches. Workflow configuration and templates alone do not enforce
these rules; required checks and branch protection enforce them at merge time.

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

For code-bearing changes, the quality job also validates `.pre-commit-config.yaml` and runs the
focused hook regression tests.
Real hook integration uses the locked development environment here; matrix jobs run the hook dispatcher
unit tests and skip integration cases when development-only tools are absent. Local hooks use the same
Ruff and Pyright settings, run on staged files, and do not replace CI enforcement. See the installation
and staging guidance in [CONTRIBUTING.md](../CONTRIBUTING.md).

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
