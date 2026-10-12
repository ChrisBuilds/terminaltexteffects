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

## Merge, artifacts, and publication

- [ ] Release PR merged; `main` CI passes for the merged commit; merged tree matches the reviewed commit.
- [ ] `tools/check_artifacts.py` passed on the release commit; wheel and sdist checksums recorded below.
- [ ] Publication approved (version, commit, tag, files):
- [ ] Tag `release-<version>` pushed to the approved commit.
- [ ] Wheel and sdist uploaded to PyPI; GitHub release created.
- [ ] Fresh PyPI install verified on the minimum supported Python.

Checksums and links:
