# Documentation deployment

The public [documentation site](https://chrisbuilds.github.io/terminaltexteffects/)
tracks development `main`, rather than a release tag or a separately edited `gh-pages`
branch. Every page identifies this policy and links the built commit when deployed.
The [PyPI package](https://pypi.org/project/terminaltexteffects/) remains the released version.

## From PR to publication

PR CI checks documentation but never publishes it. After merge, successful **push CI on
main** triggers `.github/workflows/docs.yml`. It checks that the tested SHA still equals
current main, checks out that exact SHA, installs locked tools, and builds MkDocs strictly.
The generated Pages artifact is deployed through the `github-pages` environment.
A second SHA check skips builds superseded while building or waiting for environment approval.
Failed, cancelled, fork, PR, and stale CI runs do not publish.

Only deployment has Pages-write and OIDC permissions. No branch is force-pushed and no
personal access token is required. Actions are pinned to full commit SHAs. Deployments
are serialized without cancelling an active deployment. Main can advance during an
active upload; its next successful CI run then publishes the newer site.

This rebuild runs once per successful current-main push, including source-only changes,
so generated API reference pages stay current. It does not rerun pytest or add matrix jobs.
The ordinary eight required CI checks are unchanged; deployment is a post-merge check.

## One-time cutover after the workflow PR merges

1. In repository **Settings → Pages → Build and deployment**, change **Source** from
   `Deploy from a branch` (`gh-pages`) to **GitHub Actions**. Retain the existing URL.
2. In **Settings → Environments → github-pages**, allow deployments from `main` only.
   Optional required reviewers pause each deployment; omit them for fully automatic publishing.
3. Wait for successful push CI on current main, then run **Actions → Documentation
   deployment → Run workflow**, selecting `main`, if an automatic deployment has not succeeded.
4. Check the workflow/environment deployment and public homepage, a deep API reference page,
   images, navigation, and changelog. Confirm the banner's commit matches tested main.

Keep the existing `gh-pages` branch through the cutover as a fallback. Do not delete it
as part of this change. A local strict build or a green PR check does not verify live deployment.
See [GitHub's custom Pages workflow guide](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## Retry and recovery

Manual dispatch on `main` rebuilds current main only if its push CI already succeeded.
A dispatch from another branch is skipped. If current main has failed or pending CI,
fix or rerun **CI**, then retry deployment; manual dispatch cannot bypass that gate.
Deployment failure leaves the last successful site available. Inspect the logs, Pages
source, and environment rules before retrying. Fix source problems through an issue/PR.
To undo published documentation, revert through a PR and let successful main CI redeploy.
An emergency switch back to the retained legacy branch requires a maintainer decision;
that branch may contain older documentation.

For local preview, run `./.venv/bin/python -m mkdocs serve`. For release QA, follow
[RELEASING.md](../RELEASING.md); documentation deployment does not publish PyPI packages
or GitHub releases and does not imply that development APIs exist in a released version.
