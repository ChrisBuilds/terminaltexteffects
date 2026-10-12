# Security policy

## Supported releases

Security fixes target the latest stable release on [PyPI](https://pypi.org/project/terminaltexteffects/).
Older releases don't get backports, so upgrade to the latest release. Prereleases and development
`main` don't count as a published fix. See the
[release history](https://github.com/ChrisBuilds/terminaltexteffects/blob/main/CHANGELOG.md).

## Report a vulnerability privately

Use GitHub's [Report a vulnerability](https://github.com/ChrisBuilds/terminaltexteffects/security/advisories/new)
form. Don't put exploit details in a public issue or PR.

Include the affected TTE version, Python version, operating system, relevant dependency versions,
reproduction steps or a minimal proof of concept, and the expected impact. Remove credentials and
personal information from attached input or logs.

The maintainer will assess the report, coordinate a fix and disclosure with you, and publish an
advisory and release note when appropriate. Timing depends on severity and maintainer availability;
there is no guaranteed response deadline.

For ordinary bugs, installation problems, or rendering issues, use
[public issues](https://github.com/ChrisBuilds/terminaltexteffects/issues) and the
[support guide](https://github.com/ChrisBuilds/terminaltexteffects/blob/main/SUPPORT.md).

## Dependencies and external effects

The core package has no third-party runtime dependencies. Development and documentation tools have
their own dependencies, which Dependabot keeps updated. Updating the repository lockfile doesn't
change existing installations.

User-installed effect plugins and development effects run arbitrary Python code and are not
sandboxed. Load only code you trust.
