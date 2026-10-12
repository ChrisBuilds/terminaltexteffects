# AGENTS.md

[CONTRIBUTING.md](CONTRIBUTING.md) is the authoritative development workflow. Read it before starting
work and follow it. This file adds only agent-specific rules.

## Authorization

- An issue assigned to you for implementation authorizes creating its branch, implementing the agreed
  scope, committing, pushing, opening a draft PR, marking it ready, and replying in its review threads.
  You don't need to ask again for those steps.
- Never merge, tag, publish, dismiss security alerts, or change GitHub settings without an explicit
  maintainer instruction for that action. Green CI and assignment are not merge permission.
- Get agreement before changing effect options, defaults, or visual behavior, or expanding scope.
- Fill issue and PR metadata (assignee, type and area labels, milestone if scheduled) when you create
  the issue or PR, as described in CONTRIBUTING.md.

## Tools

Prefer the repository virtualenv: `./.venv/bin/pytest`, `./.venv/bin/ruff`, `./.venv/bin/pyright`,
`./.venv/bin/python`.

- Run the narrowest test that covers the change, such as
  `./.venv/bin/pytest -n auto tests/effects_tests/test_<effect>.py`, not the whole suite after every
  edit. Broad suites run in CI.
- Don't pass `--exhaustive-effect-args` or run `-m visual`/`-m manual` tests unless asked.
- Python work is done when focused pytest, `ruff format --check`, `ruff check`, and
  `pyright --pythonpath ./.venv/bin/python` pass on the touched files. Documentation-only changes
  need only a formatting or link check.
- Add a changelog fragment and regenerate the preview for every issue.
- If CI is still running, report that and continue rather than blocking the conversation.

## Code style

- Write docstrings that reference identifiers with single backticks, such as `ParticlePool`, not
  double backticks.
- Put unfinished effects in `dev_effects/`, never `terminaltexteffects/effects/`.

## Reviews

When Codex reports a finding, reply in its thread with your intended response. After pushing a fix,
reply again with the commit and validation. If no change is needed, explain why. Resolve the thread
only after the finding is addressed. When re-review keeps producing findings, review the whole PR
yourself before requesting another round.

## After merge

When the maintainer has merged your PR, confirm that the `main` CI run and docs deployment succeeded
(`gh run list --branch main --limit 5`), report any failure, and delete the local branch and worktree.
