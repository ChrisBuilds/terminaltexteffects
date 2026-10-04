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
Python 3.9. Documentation-only changes need formatting or diff checks. Commit hooks are optional.

The `Code quality` CI job checks changed Python files, including stubs, without modifying them.
PR and branch checks compare against the merge base with the target branch; pushes to `main`
compare against the previous revision. Deleted files are excluded. Documentation-only diffs pass
without running Python tools. Changed files must pass all checks, including existing findings in
those files. Track broader cleanup separately; whole-project type checking remains the goal to
catch regressions in callers outside the changed files.

After committing, reproduce the CI checks with
`./.venv/bin/python tools/check_quality.py --base origin/main`.

GitHub Actions runs the broad default suite across supported Python versions after pushes and
on PRs. This includes shared-engine and cross-cutting changes. Broad local runs are for diagnosing
failures or explicit requests, rather than a routine prerequisite for committing or pushing.
Report pending CI and continue the conversation without waiting for the broad suites.

Run manual or visual tests when human inspection is needed. Reserve exhaustive effect-argument
testing for pre-release validation unless diagnosing the full parameter matrix. Performance
claims require before/after measurements and checks that seeded output and frame behavior are
preserved, or an explanation of intentional changes.

Regenerate shell completions when CLI options change. Update the changelog for user-facing
changes; fixes to bugs introduced in the same unreleased version do not need a separate entry.

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
[.github/README.md](.github/README.md), resolved review conversations, and enforcement for
administrators. These protections are configured in GitHub settings; repository documents
and templates do not enforce them. As a solo-maintainer project, mandatory external approvals
can remain at zero while the maintainer performs the final review.

## Agent authorization

Assigning an issue to an agent for implementation authorizes branch creation, implementation
within the agreed scope, commits, pushes, and draft PR creation. Separate permission is not
needed for those steps. Merging requires an explicit maintainer instruction. Scope changes
that alter agreed behavior require agreement before implementation.
