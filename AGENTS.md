# AGENTS.md

## Development Workflow

- Follow `CONTRIBUTING.md`: issue ticket -> branch -> pull request -> maintainer merge.
  Read `docs/development.md` for pipeline orientation. When changing CI, QA, hooks, changelog,
  release, or deployment behavior, update the authoritative instructions and affected guide sections
  in the same PR.
- When the maintainer assigns an issue for implementation, that assignment authorizes creating the branch,
  implementing the agreed scope, committing, pushing, and opening a draft PR. Do not ask again for those routine
  steps. Merging remains the maintainer's decision; never merge without an explicit instruction.
- Fill agent-created issue metadata at creation, not as later cleanup: assign `ChrisBuilds`, select exactly
  one type label (`bug`, `enhancement`, `documentation`, or `maintenance`), and add at least one relevant
  area label (`effects`, `engine`, `cli`, `ci`, or `release`). Use existing labels from this taxonomy.
- Set the intended release milestone at issue creation when the work is scheduled for a known release.
  Check current milestones; do not put the whole backlog into the next release. If unscheduled, leave the
  milestone unset and state "Release target: not scheduled" in the issue body. Do not assign a Project yet.
- At PR creation, assign `ChrisBuilds` and mirror the linked issue's type/area labels and release milestone.
  For `ChrisBuilds`-authored PRs, do not request self-review; assignment records maintainer review/merge ownership.
  For other PR authors, request `ChrisBuilds` as reviewer. This metadata never authorizes merging.
- Apply `blocked` or `needs-decision` only when an actual prerequisite or maintainer decision prevents progress,
  and explain it in the issue/PR. Do not duplicate draft status, CI results, or release milestones with labels.
- Start issue branches from up-to-date `main`, named `<type>/<issue-number>-<short-description>`.
  Do not commit development changes directly to `main` or bypass branch protection.
- Dependabot is the narrow issue-order/branch-name exception: retain its generated branch, but create/link a
  tracking issue with required metadata before merge. Triage its milestone and changelog decision per
  `.github/DEPENDENCIES.md`; add an issue-numbered fragment and regenerate the preview on the bot branch.
  Do not exempt bot PRs from changelog/CI gates or auto-merge them. Review later bot rebases again.
- Dependency gate failures require advisory remediation or graph diagnostics; never use
  warn-only, blanket exclusions, or continue-on-error. No exceptions are approved; future
  exemptions require explicit maintainer review and expiry validation per `.github/DEPENDENCIES.md`.
- Verify reported bugs and establish acceptance criteria before implementation. For changes to effect options,
  defaults, or visual behavior, present the proposed behavior and obtain agreement before changing it.
- Create unfinished effects in root `dev_effects/`, never in `terminaltexteffects/effects/`.
  Use `python -m tools.dev <effect>` or `TTE_DEV_EFFECTS_DIR` for development discovery.
  Promotion into the shipped package requires reviewed tests, docs, completions, and a changelog fragment.
  Follow `dev_effects/README.md#promotion-checklist`, run `tools/check_effect_inventory.py` with
  locked development tools, and record human visual/terminal QA; structural presence is not coverage.
- Keep commits scoped to the issue, including relevant tests, documentation, and generated artifacts. Keep local
  review notes in the sibling `dev_notes` workspace untracked and out of commits.
- Use `Closes #<issue-number>` in ordinary PR descriptions. Release PRs use `Refs #<release-issue>`
  to keep the tracking issue open until publication and verification complete; follow `RELEASING.md`.
  Describe resulting behavior and validation, and report any
  unresolved limitations. Leave the PR in draft until local verification and required CI checks pass.
- Before running project tools, check the project root for a `.venv` and prefer the tool binaries from that environment.
- Use the repo venv paths directly when available:
  - `./.venv/bin/pytest`
  - `./.venv/bin/ruff`
  - `./.venv/bin/pyright`
  - `./.venv/bin/python`

## Docstring Style

- When referencing variables, constants, methods, classes, modules, or other code identifiers in docstrings, use single backticks, such as `ParticlePool`. Do not use double backticks.

## Testing and Verification

- Use focused tests for routine development. Start with the narrowest test node or file that exercises the changed
  behavior; do not run the entire suite after every change.
- Specify a single test, a filtered group, or a complete test file as appropriate:
  - `./.venv/bin/pytest -n auto tests/engine_tests/test_terminal.py::test_<name>`
  - `./.venv/bin/pytest -n auto tests/engine_tests/test_terminal.py -k '<expression>'`
  - `./.venv/bin/pytest -n auto tests/engine_tests/test_terminal.py`
- For effect work, the usual focused command is:
  - `./.venv/bin/pytest -n auto tests/effects_tests/test_<effect>.py`
- Default pytest runs exclude tests marked `manual` or `visual`. Run those suites only when their output needs human
  inspection:
  - `./.venv/bin/pytest -m visual tests/test_effects.py`
  - `./.venv/bin/pytest -m manual tests/test_effects.py`
- Highly parametrized effect-configuration tests use deterministic pairwise coverage by default. This covers every
  parameter value and every pair of values without running the complete Cartesian product. Do not pass
  `--exhaustive-effect-args` during normal development.
- Reserve exhaustive effect-argument testing for pre-release validation:
  - `./.venv/bin/pytest -n auto --exhaustive-effect-args`
- Broad suites, including shared-engine, pytest-infrastructure, and cross-cutting changes, run in GitHub Actions
  on PRs (including drafts), pushes to `main`, and manual dispatch. Open a draft PR to test issue-branch pushes
  without duplicate runs. Strictly documentation-only changes use documentation and changelog checks instead
  of the broad pytest matrix, while preserving successful required check names. Focused CI-tool
  regressions still run in Code quality. Run broad suites locally when diagnosing failures
  or when explicitly requested;
  they are not a routine prerequisite for committing or pushing.
- Format touched Python files with `./.venv/bin/ruff format <files>` before running focused tests.
  Use safe lint fixes only (`ruff check --fix`); review unsafe fixes deliberately rather than enabling them globally.
- After targeted pytest passes, run `ruff format --check` and `ruff check` on the touched implementation and test files.
  For example:
  - `./.venv/bin/ruff format --check terminaltexteffects/effects/effect_<effect>.py tests/effects_tests/test_<effect>.py`
  - `./.venv/bin/ruff check terminaltexteffects/effects/effect_<effect>.py tests/effects_tests/test_<effect>.py`
- Optional staged-file QA hooks are configured in `.pre-commit-config.yaml`. Install with
  `./.venv/bin/pre-commit install --allow-missing-config` after syncing locked development tools.
  Hooks run safe Ruff lint fixes, formatting, read-only Pyright, and relevant changelog validation.
  Review and restage hook edits; preserve unrelated unstaged changes. Use selected-file hooks for
  routine development. Hooks do not replace focused tests or the required CI checks.
- After Ruff passes, run Pyright on those same files. For example:
  - `./.venv/bin/pyright --pythonpath ./.venv/bin/python terminaltexteffects/effects/effect_<effect>.py tests/effects_tests/test_<effect>.py`
- Install locked development tools with `uv sync --locked --group dev`. Pyright targets Python 3.9 in `pyproject.toml`.
  The `Code quality` CI job runs read-only formatting, lint, and type checks on all tracked Python files,
  including tests, tools, and archived experiments. Ignored local prototypes are excluded. Reproduce CI with `./.venv/bin/python tools/check_quality.py --all`; use
  `--base origin/main` for focused branch checks after committing.
- For workflow changes, run `./.venv/bin/python tools/check_workflows.py` with actionlint 1.7.12
  and ShellCheck installed (or `TTE_ACTIONLINT`/`TTE_SHELLCHECK` executable overrides). Follow
  `.github/CI.md#workflow-linting`; the optional workflow hook runs only in the manual stage.

## Completion Criteria

- Do not consider code work finished until focused pytest, `ruff format --check`, `ruff check`, and Pyright pass
  for touched Python implementation and test files.
- Before merging, fetch current `main` and update an outdated PR branch; retarget stacked PRs
  to `main` after prerequisites merge and incorporate their squash merges. Review integration
  conflicts and verify changed behavior. Never bypass strict branch protection or reuse stale CI.
  Refresh the next PR to merge rather than all queued branches after each main update.
- Review informational coverage changes and untested added/modified runtime lines in the Linux/Python
  3.14 summary. Missing baselines are not proof of unchanged coverage; coverage percentages do not
  replace meaningful assertions or human visual QA. Workflow edits intentionally invalidate the
  historical comparison fingerprint. Follow `.github/COVERAGE.md` for comparison rules.
- Required GitHub Actions checks must pass for the latest PR revision including current `main`
  before the work is ready to merge.
  If CI is pending, report that status instead of blocking the conversation while the broad suites run.
- Run the exhaustive effect-argument suite only as part of pre-release validation, unless the task explicitly requires
  diagnosing the complete parameter matrix.
- Documentation-only changes do not require pytest, Ruff, or Pyright; run an appropriate formatting or diff check.
- For each issue, add an issue-numbered fragment in `changelog.d` using the categories in its README. User-facing
  changes need a concise note; internal changes and fixes introduced in the same unreleased version need a
  `.skip.md` fragment explaining the exemption. Run `./.venv/bin/python tools/generate_changelog.py` and commit
  the refreshed preview with the fragment. Never edit the generated Unreleased preview directly.
- Release-preparation PRs consume pending fragments into a dated section instead of adding a new fragment.
- Run `./.venv/bin/python tools/generate_changelog.py --check` for fragment or changelog-tooling changes.
  Assemble dated releases only in release-preparation PRs as described in `CONTRIBUTING.md`; publishing requires
  an explicit maintainer instruction naming the version, commit, tag, and approved artifacts.
