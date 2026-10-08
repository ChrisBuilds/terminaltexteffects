# Focused local QA

From the repository root, use the locked Python 3.10+ development environment:

```text
uv sync --locked --group dev --python 3.14
uv run --no-sync --offline python -m tools.qa --dry-run
uv run --no-sync --offline python -m tools.qa --test tests/effects_tests/test_waves.py
uv run --no-sync --offline python -m tools.qa --test 'tests/engine_tests/test_terminal.py::test_name' -k 'case'
```

Replace example test names with existing files or nodes. Repeat `--test` for multiple
files/nodes. On POSIX, `./.venv/bin/python -m tools.qa` also works; Windows can use
`.venv\Scripts\python.exe -m tools.qa`. Commands use the active interpreter, not POSIX
shell syntax or executable paths. Nothing installs tools, fetches Git, modifies source,
automatically fixes formatting, retries failures, or launches the broad test suite.
The strict MkDocs build writes its normal ignored `site/` output.

## Selection and execution

`--base` defaults to your local `origin/main`; fetch it before checking if it is stale.
Selection includes committed branch changes since the merge base, staged and unstaged
changes, and untracked files that Git does not ignore. Checks read current working-tree
contents, **not a snapshot of the index or committed revision**. Both rename paths and
deletions influence the plan; deleted files and symlinks are not passed to file checks.
Ignored experiments are excluded. A bad or unavailable base fails instead of silently
selecting nothing. This is a local branch check, not a CI classifier replacement.

The command prints paths, reasons and argument lists before running:

- Existing changed text: reuse hook hygiene, preserving Markdown hard breaks.
- Explicit `--test` files/nodes: focused pytest, optionally filtered by `-k`. Directories,
  absolute paths, parent traversal and pytest options are rejected as test selections.
  Without `--test`, the command explicitly reports **Tests NOT RUN**.
- Existing changed Python/stub files: read-only Ruff format, lint and Pyright.
- Any changes: validate changelog fragments and generated preview. Before committing,
  this does not verify the committed branch's issue-numbered changelog decision;
  run `tools/generate_changelog.py --check --base origin/main` after committing.
- Workflow inputs: all tracked workflows plus existing changed workflows (including
  untracked files) through the actionlint/ShellCheck helper; install its external tools or
  use the overrides described in [CI.md](CI.md#workflow-linting).
- Runtime or completion-generator inputs: generated shell completion freshness.
- Effect inventory inputs: changes under `terminaltexteffects/`, `docs/effects/`, or
  `tests/effects_tests/`, plus `mkdocs.yml` and `tools/check_effect_inventory.py`, run the
  structural check for CLI registration, nonempty effect docs/navigation, and permanent test
  definitions. Test-file changes, including deletions, also detect missing or empty tests.
- Documentation/API inputs: strict MkDocs build, using the same input classification
  helper as CI.

`--dry-run` only reads Git and validates test selections; it does not execute checks.
Normal execution stops at the first failure and preserves the tool's exit status.
After fixing a failure, rerun the command. Format touched Python files before running
QA. Neither a successful preview nor a run without tests establishes tested behavior.
Choose meaningful focused tests yourself, including executable-documentation regressions
when canonical examples change; there is no automatic test-to-source mapping.

## What remains in CI and human review

CI still checks every tracked Python file and runs the broad platform/version matrix,
dependency review, artifacts, hook regressions and other integration gates. The helper
provides focused local feedback, not every CI step. Missing tools fail when their check
runs. Visual/manual effect QA and exhaustive pre-release testing remain separate.
The command does not commit, push, mark a PR ready or authorize merging.
