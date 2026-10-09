---
name: Release preparation
about: Prepare a release and record automated QA, human QA, and publication approval.
title: 'Release <version>'
assignees: ChrisBuilds
labels: maintenance, release
---

Follow the [release runbook](https://github.com/ChrisBuilds/terminaltexteffects/blob/main/RELEASING.md). Update this issue as evidence becomes available.
Use N/A with a reason for checks that do not apply. A checked box needs a result or evidence link.

## Release identity

- Version and intended date:
- Supported Python versions:
- Included issues and migration notes:
- Release branch and PR (`Refs #this-issue`; keep this issue open until verified publication):
- Reviewed head SHA:
- Merged release SHA:
- Tag (`release-<version>`):

## Preparation and automated QA

- [ ] Finished effects promoted through reviewed PRs; prototypes remain outside the shipped package.
- [ ] Version, lockfile, Python requirement, and support documentation agree.
- [ ] Fragments reviewed; dated Towncrier notes assembled and fragments consumed in the release PR.
- [ ] Changelog preview and branch decision checks pass.
- [ ] Focused code QA passes; release-relevant existing quality findings reviewed.
- [ ] All required CI checks actually pass for the latest release PR revision; full test matrix ran.
- [ ] Manual exhaustive workflow completed successfully on the latest candidate; record run link, candidate/workflow SHAs, Python version, exit status, inspected results/skips, and downloaded evidence (30-day retention).
- [ ] Strict docs build and completion freshness checks pass.
- [ ] Security health review recorded: both CodeQL uploads/freshness, uncovered candidate changes, dependency alerts/updater health and tracked limitations.
- [ ] Automated review completed; findings addressed and conversations resolved.

## Human QA

- [ ] Changed effects inspected for appearance, pacing, and final text.
- [ ] Representative small/multiline/sparse/wide-character inputs checked.
- [ ] Relevant ANSI styles, color modes, and existing-color handling checked.
- [ ] Narrow/wide terminals, wrapping/clipping, resize behavior, interruption, and cursor restoration checked.
- [ ] Relevant canvas/anchoring scenarios inspected directly where automated visual tests are skipped.
- [ ] Relevant performance changes measured; seeded output/frame invariants verified or changes explained.

Record terminals, OS versions, selections/commands, results, and reasons for N/A here:

## Merge and artifacts

- [ ] Maintainer authorized merge; release PR squash-merged.
- [ ] Final merged commit identified and its main CI passed; reviewed/merged trees compared, with exhaustive validation rerun if they differ.
- [ ] Exact approved commit built in a clean checkout with locked tools.
- [ ] Wheel, source archive, and source-rebuilt wheel pass artifact validation and clean-install checks.
- [ ] Development effects absent from all archives, installed CLI, and bundled completions.
- [ ] Two upload filenames and SHA-256 checksums recorded; rebuilt duplicate excluded.
- [ ] Version, dated notes, tag name, and artifact metadata agree; release version/tag unused.

Artifact evidence and checksums:

## Publication approval

Approval must explicitly name the version, commit, tag, and selected artifacts.
Preparation or merge approval alone does not authorize publishing.

- Approver and approval link/date:
- Approved version, full SHA, tag, and artifact/checksum record:

## Publication and post-release verification

- [ ] Merged release security-relevant changes covered by verified main scans; open findings/limitations reviewed.
- [ ] Explicit publication approval recorded.
- [ ] Remote tag points to the approved commit.
- [ ] Exact approved wheel and source archive uploaded to PyPI.
- [ ] GitHub release published from the existing tag using the dated changelog section.
- [ ] Fresh PyPI installation outside the checkout works on minimum supported Python.
- [ ] Package/effect imports, version, both CLI commands, and a short effect run verified.
- [ ] Published metadata and checksums match approved artifacts.
- [ ] Public docs verified current, or deployment follow-up explicitly recorded.
- [ ] Release URLs, results, and remaining follow-ups recorded; release sign-off complete.

PyPI, GitHub release, documentation, and verification links:
