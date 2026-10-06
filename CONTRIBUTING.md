# Development process

New to TTE? Start with the [developer pipeline guide](docs/development.md) for an explanation
of each stage, its purpose, triggers, tooling, and completion criteria. This file defines
the contribution rules; the guide explains how they fit together.

Development follows an issue ticket -> branch -> pull request -> maintainer merge process.
Use one issue and one PR for a coherent change. Track unrelated discoveries in separate issues.

For compatibility and ordinary bug reports, see [SUPPORT.md](SUPPORT.md). Report vulnerabilities
privately as described in [SECURITY.md](SECURITY.md); keep exploit details out of public tickets,
fragments, and PRs until coordinated disclosure.

Dependabot's generated update PRs are the narrow exception to issue-first creation and branch
naming. Before merging, create/link a tracking issue, complete metadata and the changelog
decision, and require latest CI. Follow [dependency update triage](.github/DEPENDENCIES.md).

## 1. Define the issue

Describe the problem or desired behavior, scope, and acceptance criteria. Bug reports should
include reproduction steps, expected and actual behavior, and relevant environment information.
Fill agent-created issue metadata **when creating the issue**:

- Assignee: `ChrisBuilds`, as the accountable maintainer even when an agent implements the change.
- Type: exactly one of `bug`, `enhancement`, `documentation`, or `maintenance`.
- Area: one or more of `effects`, `engine`, `cli`, `ci`, or `release`.
- Milestone: the intended release when scheduled. Check current milestones and select only a release
  this work is intended to ship in. Unscheduled work leaves the milestone unset and includes
  `Release target: not scheduled` in its body; do not invent a target to fill the field.
- Project: leave unset for now. Issues, PRs, CI, and release milestones are sufficient for this workflow.

Reuse the agreed labels; do not add synonyms for existing categories. The `ci` area includes QA
and development workflow tooling. Add `blocked` or `needs-decision` only for an actual impediment,
with a reason in the issue/PR; remove it when resolved. Draft status, CI results, and milestones
already describe readiness and release targets, so they do not need extra labels. Other existing
labels may remain for their original purposes.

For example, coverage reporting uses `maintenance` + `ci`; PowerShell completion uses
`enhancement` + `cli`. A scheduled issue can be created with all metadata in one command:

```sh
gh issue create --title 'Describe the change' --body-file /path/to/issue.md \
  --assignee ChrisBuilds --label maintenance --label ci --milestone 0.16.0
```

Use the actual approved release milestone; `0.16.0` is an example, not a permanent default.
The issue templates supply owner/type defaults (and the release area for release preparation).
They cannot choose a dynamic release milestone or infer every area: agents must set those
fields explicitly through GitHub or the CLI **before submission**. Verify the resulting metadata.
External reports may need maintainer triage; these creation requirements apply to agent-managed work.

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
validation; staged deletions and both sides of renames are included. The changelog hook copies
its inputs and renderer from the Git index into a temporary directory, so untracked fragments
and unstaged edits cannot affect validation. It leaves working files and staging untouched.
CI checks the issue's changelog decision against committed revisions.

If a hook changes files, review and stage those fixes, then retry the commit. Pre-commit temporarily
sets aside unstaged tracked changes and restores them afterward. If those changes conflict with
automatic fixes, it rolls back the fixes and preserves your unstaged work; format the file deliberately,
then stage only the intended changes. Hook installation permits older branches without a configuration
to skip hooks. Keep the development environment synced when switching branches.

To run hooks manually on selected files:

```bash
./.venv/bin/pre-commit run --files tools/example.py tests/test_example.py
```

Use selected-file hooks for routine development. Focused pytest remains a development QA
step; broad compatibility suites remain in CI.

Workflow edits also have a read-only actionlint/ShellCheck command and an optional manual-stage
`workflows` hook. Install the pinned actionlint release and ShellCheck before invoking it; see
[workflow linting](.github/CI.md#workflow-linting). Code quality enforces this check on every run.

Hooks are optional and bypassable, so successful CI checks remain the enforced merge gate. Remove the local installation with
`./.venv/bin/pre-commit uninstall`.

The `Code quality` CI job checks every tracked Python file, including stubs, without modifying
them. This includes implementation, tests, tools, and archived experiments, so changes cannot
silently break types in unchanged callers. Ignored and untracked local prototypes are excluded.
Documentation-only changes still run these read-only quality checks but skip pytest.

Reproduce the full CI quality checks with
`./.venv/bin/python tools/check_quality.py --all`.
For a focused branch check after committing, use
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
runs. This builds a wheel and source distribution from a temporary copy of tracked files with
an isolated, locked build backend,
then rebuilds a wheel from the source archive. All three distributions must include the
tracked runtime files, match project metadata, and pass `twine check --strict` for metadata
and README rendering. Each wheel is installed into a separate temporary environment outside
the checkout; package and effect imports, both CLI entry points, and a seeded effect run
must work. The existing Python matrix continues to check supported interpreter versions.

To reproduce after syncing development tools, stage newly added project files so the
tracked-file copy includes them, then run:

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

Develop unfinished effects in the repository-root `dev_effects/` directory. Run them with
`./.venv/bin/python -m tools.dev <effect>` or set `TTE_DEV_EFFECTS_DIR` for parser-based tools.
The launcher opts in explicitly; normal CLI use and bundled completions remain independent
of prototypes. Both build targets exclude development effects, and artifact validation injects
prototypes into a temporary source copy to verify that exclusion. See the
[development effect workflow](dev_effects/README.md) for tests and promotion into the shipped package.

Regenerate shell completions when CLI options change. Add an issue-numbered fragment in
`changelog.d` for each change, then refresh the generated Unreleased preview with
`./.venv/bin/python tools/generate_changelog.py`. User-facing changes need a concise note;
internal changes and fixes introduced in the same unreleased version need a `.skip.md` fragment
explaining why no release note is needed. See [fragment guidance](changelog.d/README.md).

## 4. Open the pull request

Open a draft PR targeting `main`. At creation, assign `ChrisBuilds` and copy the linked issue's
labels and milestone. Do not assign a Project. If the author is `ChrisBuilds`, do not request
self-review: the assignee records maintainer review/merge responsibility. For another author,
request `ChrisBuilds` as reviewer. Assignment is ownership, not a formal approval or merge permission.

Include `Closes #<issue-number>` (release tracking PRs use
`Refs #<release-issue>`), explain resulting behavior,
record local validation, and identify remaining limitations. Draft PRs may be opened early for
discussion and CI feedback. Fix failures on the same branch and update the PR description when
scope changes.

Once focused local checks and required CI checks pass for the latest revision, mark the PR ready
for review. The maintainer verifies acceptance criteria and resolves outstanding discussions.

## 5. Merge and close

The maintainer decides when to merge. Use squash merging for one coherent commit per issue,
then delete the branch. Ordinary linked issues close when the PR merges into `main`;
release tracking issues remain open through publication and post-release verification.

The `main` protection requires PRs, all ten checks listed in
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

Follow [RELEASING.md](RELEASING.md) for the complete release process: version/lockfile
updates, Towncrier assembly, automated and human QA, maintainer review, exact artifact
approval, manual publishing, and post-release verification. Use the
[release issue template](.github/ISSUE_TEMPLATE/release.md) to record evidence and approvals.

Release tracking issues stay open through publication. Release PRs use `Refs #<release-issue>`
instead of auto-closing that issue on merge; ordinary development PRs continue to use `Closes`.
Preparation and merge approval do not authorize tagging or publishing. Publishing automation
is deferred; follow the documented manual procedure with explicit maintainer authorization.

## Public documentation

The public site follows development `main` after successful main push CI, with a banner
linking the built commit. PRs validate docs without publishing. See
[documentation deployment](.github/DOCUMENTATION.md) for setup, local preview, and recovery.
