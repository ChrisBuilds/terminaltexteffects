# Development process

Development follows an issue ticket -> branch -> pull request -> maintainer merge process.
Use one issue and one PR for a coherent change. Track unrelated discoveries in separate issues.

## 1. Define the issue

Describe the problem or desired behavior, scope, and acceptance criteria. Bug reports should
include reproduction steps, expected and actual behavior, and relevant environment information.
Assign a release milestone when appropriate.

Verify reported bugs before implementing a fix. Agree on changes to effect options, defaults,
and visual behavior before implementation. Record the agreed behavior in the issue.

## 2. Create the branch

Start from up-to-date `main`. Name the branch `<type>/<issue-number>-<short-description>`:

- `fix/123-python-39-compatibility`
- `feat/124-new-effect`
- `docs/125-api-examples`

Commit development changes on the issue branch. Do not push changes directly to `main` or
bypass its protection. Keep commits focused, with related tests, documentation, and generated
artifacts included. Local review notes in the sibling `dev_notes` workspace remain untracked.

## 3. Implement and verify locally

Use the repository's `.venv` tools when available. Follow the commands and focused verification
requirements in [AGENTS.md](AGENTS.md): format touched Python files with Ruff, run focused pytest,
then check formatting, lint, and types. Install reproducible tools with `uv sync --locked --group dev`.
Ruff applies safe fixes by default; apply unsafe fixes only after deliberate review. Pyright targets
Python 3.9. Documentation-only changes need formatting or diff checks.

Optional pre-commit hooks catch formatting, lint, type, and changelog problems before committing.
Install them once per clone after syncing the locked development environment:

```bash
uv sync --locked --group dev
./.venv/bin/pre-commit install --allow-missing-config
```

Hooks use this checkout's `.venv`, avoiding separate Ruff/Pyright versions or isolated environments
without project dependencies. Staged Python files and stubs run safe Ruff lint fixes, Ruff formatting,
then read-only Pyright with the Python 3.9 target. Related changelog files trigger fragment and preview
validation; staged deletions and both sides of renames are included. This local check validates the
pending snapshot, while CI checks the issue's changelog decision against committed revisions.

If a hook changes files, review and stage those fixes, then retry the commit. Pre-commit temporarily
sets aside unstaged tracked changes and restores them afterward. If those changes conflict with
automatic fixes, it rolls back the fixes and preserves your unstaged work; format the file deliberately,
then stage only the intended changes. Hook installation permits older branches without a configuration
to skip hooks. Keep the development environment synced when switching branches.

To run hooks manually on selected files:

```bash
./.venv/bin/pre-commit run --files tools/example.py tests/test_example.py
```

Do not use `--all-files` as a routine check while whole-project quality cleanup is pending.
Focused pytest remains a development QA step; broad compatibility suites remain in CI. Hooks are
optional and bypassable, so successful CI checks remain the enforced merge gate. Remove the local
installation with `./.venv/bin/pre-commit uninstall`.

The `Code quality` CI job checks changed Python files, including stubs, without modifying them.
PR and branch checks compare against the merge base with the target branch; pushes to `main`
compare against the previous revision. Deleted files are excluded. Documentation-only diffs pass
without running Python tools. Changed files must pass all checks, including existing findings in
those files. Track broader cleanup separately; whole-project type checking remains the goal to
catch regressions in callers outside the changed files.

After committing, reproduce the CI checks with
`./.venv/bin/python tools/check_quality.py --base origin/main`.

GitHub Actions runs the broad default suite across supported Python versions on PRs (including
drafts), pushes to `main`, and manual dispatch. Issue-branch pushes use the open PR's run;
open a draft PR or use manual dispatch to check a branch without a PR. Strictly documentation-only
changes run documentation and changelog checks, with successful required matrix check names
without executing pytest. Code, dependency, packaging, test, and CI changes retain the full matrix.
This includes shared-engine and cross-cutting changes. Broad local runs are for diagnosing
failures or explicit requests, rather than a routine prerequisite for committing or pushing.
Report pending CI and continue the conversation without waiting for the broad suites.

Release artifacts are validated once in `Code quality` for code-bearing changes and manual
runs. This builds a wheel and source distribution with an isolated, locked build backend,
then rebuilds a wheel from the source archive. All three distributions must include the
tracked runtime files, match project metadata, and pass `twine check --strict` for metadata
and README rendering. Each wheel is installed into a separate temporary environment outside
the checkout; package and effect imports, both CLI entry points, and a seeded effect run
must work. The existing Python matrix continues to check supported interpreter versions.

To reproduce after syncing development tools, run:

```sh
./.venv/bin/python tools/check_artifacts.py
```

Temporary builds and environments are removed automatically. Optionally pass
`--output-dir /path/to/empty-directory` to retain the distributions for inspection.
This check does not publish artifacts. Documentation-only changes skip artifact validation.

Run manual or visual tests when human inspection is needed. Reserve exhaustive effect-argument
testing for pre-release validation unless diagnosing the full parameter matrix. Performance
claims require before/after measurements and checks that seeded output and frame behavior are
preserved, or an explanation of intentional changes.

Regenerate shell completions when CLI options change. Add an issue-numbered fragment in
`changelog.d` for each change, then refresh the generated Unreleased preview with
`./.venv/bin/python tools/generate_changelog.py`. User-facing changes need a concise note;
internal changes and fixes introduced in the same unreleased version need a `.skip.md` fragment
explaining why no release note is needed. See [fragment guidance](changelog.d/README.md).

## 4. Open the pull request

Open a draft PR targeting `main`. Include `Closes #<issue-number>`, explain resulting behavior,
record local validation, and identify remaining limitations. Draft PRs may be opened early for
discussion and CI feedback. Fix failures on the same branch and update the PR description when
scope changes.

Once focused local checks and required CI checks pass for the latest revision, mark the PR ready
for review. The maintainer verifies acceptance criteria and resolves outstanding discussions.

## 5. Merge and close

The maintainer decides when to merge. Use squash merging for one coherent commit per issue,
then delete the branch. The linked issue closes when the PR merges into `main`.

The `main` protection requires PRs, all eight checks listed in
[.github/CI.md](.github/CI.md), resolved review conversations, and enforcement for
administrators. These protections are configured in GitHub settings; repository documents
and templates do not enforce them. As a solo-maintainer project, mandatory external approvals
can remain at zero while the maintainer performs the final review.

## Agent authorization

Assigning an issue to an agent for implementation authorizes branch creation, implementation
within the agreed scope, commits, pushes, and draft PR creation. Separate permission is not
needed for those steps. Merging requires an explicit maintainer instruction. Scope changes
that alter agreed behavior require agreement before implementation.

## Release notes

`CHANGELOG.md` is the canonical user-facing history. Its Unreleased preview is generated from
Towncrier fragments; never edit that block directly. New PRs add a real issue-numbered fragment,
or an explicit skip-reason fragment. The `Code quality` job validates fragment names and content,
preview freshness, and the branch's changelog decision. Published history before 0.16.0 retains
its original format. The ChangeBlog is optional and holds demos or extended explanations.

Prepare release notes in a dedicated release issue and PR after reviewing all pending fragments:

1. Run `uv sync --locked --group dev` and preview with
   `./.venv/bin/towncrier build --draft --version 0.16.0 --date YYYY-MM-DD`.
2. Edit fragments to consolidate overlapping notes and make migration instructions clear.
3. Clear the generated preview with `./.venv/bin/python tools/generate_changelog.py --clear`.
4. Assemble the dated section with
   `./.venv/bin/towncrier build --yes --version 0.16.0 --date YYYY-MM-DD`.
   Towncrier inserts it above published history and consumes the fragments, including skip reasons.
5. Refresh the now-empty preview with `./.venv/bin/python tools/generate_changelog.py`, update
   the project version, and commit the release section and fragment deletions together.
6. Review the release PR and complete pre-release validation. After the maintainer authorizes
   publishing, use the same dated section for the GitHub release. Documentation includes the
   canonical changelog directly; it does not require a separately maintained copy.

Substitute the intended version and actual release date for the examples. Release preparation
does not authorize merging, creating a release tag, or publishing packages or a GitHub release.

After committing, check the branch's changelog decision with
`./.venv/bin/python tools/generate_changelog.py --check --base origin/main`.
Preview edits alone do not satisfy this check; release PRs must consume fragments into a new dated section.
