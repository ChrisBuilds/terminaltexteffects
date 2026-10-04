# AGENTS.md

## Development Workflow

- Follow `CONTRIBUTING.md`: issue ticket -> branch -> pull request -> maintainer merge.
- When the maintainer assigns an issue for implementation, that assignment authorizes creating the branch,
  implementing the agreed scope, committing, pushing, and opening a draft PR. Do not ask again for those routine
  steps. Merging remains the maintainer's decision; never merge without an explicit instruction.
- Start issue branches from up-to-date `main`, named `<type>/<issue-number>-<short-description>`.
  Do not commit development changes directly to `main` or bypass branch protection.
- Verify reported bugs and establish acceptance criteria before implementation. For changes to effect options,
  defaults, or visual behavior, present the proposed behavior and obtain agreement before changing it.
- Keep commits scoped to the issue, including relevant tests, documentation, and generated artifacts. Keep local
  review notes in the sibling `dev_notes` workspace untracked and out of commits.
- Use `Closes #<issue-number>` in the PR description, describe resulting behavior and validation, and report any
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
  after pushes and on PRs. Run broad suites locally when diagnosing failures or when explicitly requested;
  they are not a routine prerequisite for committing or pushing.
- Format touched Python files with `./.venv/bin/ruff format <files>` before running focused tests.
  Use safe lint fixes only (`ruff check --fix`); review unsafe fixes deliberately rather than enabling them globally.
- After targeted pytest passes, run `ruff format --check` and `ruff check` on the touched implementation and test files.
  For example:
  - `./.venv/bin/ruff format --check terminaltexteffects/effects/effect_<effect>.py tests/effects_tests/test_<effect>.py`
  - `./.venv/bin/ruff check terminaltexteffects/effects/effect_<effect>.py tests/effects_tests/test_<effect>.py`
- After Ruff passes, run Pyright on those same files. For example:
  - `./.venv/bin/pyright --pythonpath ./.venv/bin/python terminaltexteffects/effects/effect_<effect>.py tests/effects_tests/test_<effect>.py`
- Install locked development tools with `uv sync --locked --group dev`. Pyright targets Python 3.9 in `pyproject.toml`.
  The `Code quality` CI job runs read-only formatting, lint, and type checks on changed Python files. To reproduce
  its branch checks locally, run `./.venv/bin/python tools/check_quality.py --base origin/main` after committing.

## Completion Criteria

- Do not consider code work finished until focused pytest, `ruff format --check`, `ruff check`, and Pyright pass
  for touched Python implementation and test files.
- Required GitHub Actions checks must pass for the latest PR revision before the work is ready to merge.
  If CI is pending, report that status instead of blocking the conversation while the broad suites run.
- Run the exhaustive effect-argument suite only as part of pre-release validation, unless the task explicitly requires
  diagnosing the complete parameter matrix.
- Documentation-only changes do not require pytest, Ruff, or Pyright; run an appropriate formatting or diff check.
- For each issue, add an issue-numbered fragment in `changelog.d` using the categories in its README. User-facing
  changes need a concise note; internal changes and fixes introduced in the same unreleased version need a
  `.skip.md` fragment explaining the exemption. Run `./.venv/bin/python tools/generate_changelog.py` and commit
  the refreshed preview with the fragment. Never edit the generated Unreleased preview directly.
- Run `./.venv/bin/python tools/generate_changelog.py --check` for fragment or changelog-tooling changes.
  Assemble dated releases only in release-preparation PRs as described in `CONTRIBUTING.md`; publishing requires
  an explicit maintainer instruction.
