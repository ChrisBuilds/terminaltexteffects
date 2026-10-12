---
name: Release preparation
about: Prepare a release and record QA and publication approval.
title: 'Release <version>'
assignees: ChrisBuilds
labels: maintenance, release
---

Follow [RELEASING.md](https://github.com/ChrisBuilds/terminaltexteffects/blob/main/RELEASING.md).
Mark items that don't apply as N/A with a reason.

- Version / date:
- Release PR (`Refs #this-issue`):
- Release commit (full SHA):

## Preparation and automated QA

- [ ] Version, `uv.lock`, and SUPPORT.md updated.
- [ ] Fragments reviewed and assembled into a dated changelog section.
- [ ] Required CI passes on the latest release PR commit.
- [ ] Exhaustive workflow passed on the candidate SHA (run link:).
- [ ] No untriaged Code scanning or Dependabot alerts.

## Human QA

- [ ] Changed effects inspected: appearance, pacing, final text.
- [ ] Varied input (small, multiline, sparse, wide characters) and color modes checked.
- [ ] Terminal sizes, interruption, and cursor restoration checked.

Terminals, platforms, and notes:

## Merge and publication

- [ ] Release PR merged; `main` CI passes for the merged commit; merged tree matches the reviewed commit.
- [ ] TestPyPI dry run of the release workflow succeeded (run link:), if the workflow changed since the last release.
- [ ] Publication approved (version, commit):
- [ ] Tag `release-<version>` pushed; build job passed; checksums recorded below.
- [ ] `pypi` environment approved; PyPI upload and GitHub release succeeded (run link:).
- [ ] Fresh PyPI install verified on the minimum supported Python; attestations shown on PyPI.

Checksums and links:
