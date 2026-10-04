# Continuous integration

The development process is defined in [CONTRIBUTING.md](../CONTRIBUTING.md).
Focused verification runs locally; broad default suites run here after pushes and on PRs.
Broad local runs are reserved for diagnosing failures or explicit requests.

`workflows/ci.yml` runs on pushes, pull requests, and manual dispatch. Local commits
start these checks once pushed to GitHub; no local commit hook or private runner is needed.

The matrix runs the default pytest suite on Python 3.9 through 3.14 using Ubuntu 24.04.
It uses locked test dependencies, installs a non-editable package, and checks package import
and CLI startup from outside the checkout. Bash and Zsh completion behavior is covered by
the tests, and a separate job checks that the committed completion scripts are current.
Manual, visual, and exhaustive effect-argument tests remain outside this workflow.

New pushes cancel obsolete runs for the same branch or pull request. Each Python version
reports separately, and a failure on one version does not cancel the other matrix jobs.

The intended protection for `main` requires these checks before merging:

- `Python 3.9`
- `Python 3.10`
- `Python 3.11`
- `Python 3.12`
- `Python 3.13`
- `Python 3.14`
- `Shell completions`
- `Code quality`

Configure GitHub branch protection to require PRs, the checks above, resolved conversations,
and enforcement for administrators. Keep mandatory external approvals at zero for solo
maintenance; the maintainer still reviews and decides when to merge. Use squash merging
and delete merged issue branches. Workflow configuration and templates alone do not enforce
these rules; required checks and branch protection enforce them at merge time.

When changing the minimum supported Python version or adding a supported version, update
the matrix alongside `pyproject.toml` and `tox.ini`.

`Code quality` runs once on Python 3.14 with locked development dependencies. Ruff checks
formatting and lint; Pyright checks types targeting Python 3.9. These checks are read-only
and cover changed Python files and stubs, including rename destinations and excluding deleted
files. PRs compare with their target branch's merge base; branch pushes compare with `main`;
pushes to `main` compare with the previous revision. No Python changes means a passing check.

Whole-project quality enforcement is deferred while existing findings are cleaned up in separate
issues. All findings in changed files must be resolved. Once this job has run on GitHub, add
`Code quality` to the required branch-protection checks alongside the existing seven jobs.
