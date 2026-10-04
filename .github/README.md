# Continuous integration

`workflows/ci.yml` runs on pushes, pull requests, and manual dispatch. Local commits
start these checks once pushed to GitHub; no local commit hook or private runner is needed.

The matrix runs the default pytest suite on Python 3.9 through 3.14 using Ubuntu 24.04.
It uses locked test dependencies, installs a non-editable package, and checks package import
and CLI startup from outside the checkout. Bash and Zsh completion behavior is covered by
the tests, and a separate job checks that the committed completion scripts are current.
Manual, visual, and exhaustive effect-argument tests remain outside this workflow.

New pushes cancel obsolete runs for the same branch or pull request. Each Python version
reports separately, and a failure on one version does not cancel the other matrix jobs.

After the workflow has run on GitHub, configure a branch ruleset or branch protection rule
for the default branch to require these checks before merging:

- `Python 3.9`
- `Python 3.10`
- `Python 3.11`
- `Python 3.12`
- `Python 3.13`
- `Python 3.14`
- `Shell completions`

Require pull requests for changes to the protected branch so failed checks cannot be
bypassed by a direct push. Workflow configuration alone reports failures; required checks
and the branch rule enforce them at merge time.

When changing the minimum supported Python version or adding a supported version, update
the matrix alongside `pyproject.toml` and `tox.ini`.

Repo-wide Ruff and Pyright checks are not yet enforced by this workflow because the repo
has existing findings. Focused lint and type checks remain part of the development workflow.
