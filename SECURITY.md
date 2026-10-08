# Security policy

## Supported releases

Security fixes target the latest stable release published on PyPI. Older releases do
not receive security backports; upgrade to the latest stable release. Prereleases and
development `main` are not substitutes for a published security fix.

The latest stable release is currently 0.15.0. When a new stable release is published,
it becomes the supported release. Maintainers update this document during release preparation.
See the [release history](https://github.com/ChrisBuilds/terminaltexteffects/blob/main/CHANGELOG.md)
for fixes and migration notes.

## Report a vulnerability privately

Use GitHub's [Report a vulnerability](https://github.com/ChrisBuilds/terminaltexteffects/security/advisories/new)
form. Private vulnerability reporting is enabled for this repository. The report is
shared privately with the maintainers; do not put exploit details in a public issue or PR.

Include the affected TTE version, Python version, operating system, relevant dependency
versions, reproduction steps or a minimal proof of concept, and the expected security impact.
Remove credentials and personal information from attached input or logs.

Maintainers assess the report, coordinate a fix and disclosure with the reporter, and
publish a security advisory and release note when appropriate. Response and release timing
depend on maintainer availability and severity; there is no guaranteed response deadline.

For ordinary bugs, installation problems, or visual rendering issues, use
[public issues](https://github.com/ChrisBuilds/terminaltexteffects/issues) and the
[support guide](https://github.com/ChrisBuilds/terminaltexteffects/blob/main/SUPPORT.md).

## Dependencies and external effects

The core package has no third-party runtime dependencies. Optional documentation and
development/release tools have their own dependency graph; Dependabot security updates
are reviewed and tested through the normal PR process. Updating the repository lockfile
does not update an existing installation or publish a new package release.

User-installed plugins and opted-in development effects execute Python code. Load only
code you trust; external effects are not sandboxed. Do not include private exploit details
in dependency-tracking issues, changelog fragments, or PRs before coordinated disclosure.

## Maintainer monitoring

Maintainers follow the [security monitoring procedure](https://github.com/ChrisBuilds/terminaltexteffects/blob/main/.github/SECURITY_MONITORING.md)
for weekly and pre-release alert review, scan freshness, notification ownership and
failure escalation. Automatic scans and a passing PR are not proof that every finding
has been resolved. This internal maintenance cadence does not promise a response deadline
for private reports.
