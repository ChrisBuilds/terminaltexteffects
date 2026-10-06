# Release runbook

Use this procedure for each release. Copy the [release checklist](.github/ISSUE_TEMPLATE/release.md)
into a release issue and record evidence there. The issue tracks the release branch, PR,
exact commits tested, QA results, artifacts, approval, and publication links.

Preparing a release authorizes preparation and QA. Merging requires the maintainer's
instruction; tagging, PyPI upload, and publishing a GitHub release require explicit
publication approval for the version and commit. A green CI run does not grant that approval.

## 1. Open the release issue and branch

Start from current `main` and use `release/<issue-number>-<version>` for the branch.
Record the intended version, release date, Python support, included issues, and any
migration instructions. The next planned release is 0.16.0 with Python 3.9.2 minimum.
Do not change the version or create a tag merely while improving this runbook.

Sync locked tools with `uv sync --locked --group dev`. Keep prototypes in `dev_effects/`;
promote finished effects through their own reviewed PRs before preparing the release.

## 2. Prepare the version and release notes

Update `[project].version` in `pyproject.toml` to the intended release version, then run
`uv lock` to refresh project metadata in `uv.lock`, followed by
`uv sync --locked --group dev` to refresh the editable installation and its version metadata.
Keep `requires-python`, supported-version CI, and compatibility documentation consistent.
Use the following commands with the actual version and publication date:

```sh
./.venv/bin/towncrier build --draft --version 0.16.0 --date YYYY-MM-DD
```

Review pending fragments for accuracy, duplicates, breaking changes, and migration guidance.
The template omits internal skip reasons from published notes. Keep the original format of
history before 0.16.0; new releases use the configured Towncrier sections.

```sh
./.venv/bin/python tools/generate_changelog.py --clear
./.venv/bin/towncrier build --yes --version 0.16.0 --date YYYY-MM-DD
./.venv/bin/python tools/generate_changelog.py
```

Commit the version, lockfile, dated release section, and consumed fragments together.
Release preparation consumes existing fragments; it does not need a new release fragment.
After committing, verify with:

```sh
./.venv/bin/python tools/generate_changelog.py --check --base origin/main
```

If the publication date changes, update the new dated release heading through the release
PR and rerun checks. Do not modify already published release history.

## 3. Open the release PR and complete automated QA

Open a draft PR with `Refs #<release-issue>`, keeping the tracking issue open until
publication and post-release verification finish. Link the checklist, describe the release scope,
and record the head SHA. Follow the usual focused local QA for changed code and resolve every
required CI failure. Required checks are listed in [.github/CI.md](.github/CI.md).

The default CI matrix covers Python 3.9–3.14, shell completions, whole-project formatting/lint/types,
changelog validation, relevant strict documentation builds, and artifact validation for code-bearing
changes. Documentation-only successful check names are not evidence that tests actually ran.
Release version and packaging changes must execute the full matrix.

Pre-release QA additionally runs the exhaustive effect-argument suite:

```sh
./.venv/bin/pytest -n auto --exhaustive-effect-args --durations=20
```

This is separate from routine pairwise CI. Run it as a dedicated pre-release task, record the
Python version, exact SHA, exit status, and log, and allow it to finish. It is not a routine local
commit prerequisite. A skipped, interrupted, or partial run is not a passing exhaustive result.

CI enforces whole-project Ruff formatting, lint, and Pyright checks on tracked Python files.
Record any remaining release-relevant findings in the issue.

## 4. Complete human QA

Inspect changed effects in a real terminal using representative small, multiline, sparse, and
wide-character inputs. Compare pacing and appearance with the intended behavior. Check ANSI
styles and colors, `ignore`/`always`/`dynamic` existing-color handling where relevant, truecolor,
XTerm colors, and no-color output. Check narrow/wide terminals, clipping/wrapping, interruption,
and cursor restoration. Test resizing for regressions; this is not a promise of live reflow.

Use focused visual selections, without parallel workers and with output capture disabled:

```sh
./.venv/bin/pytest -s -m visual tests/test_effects.py -k 'Wipe'
./.venv/bin/pytest -s -m manual tests/test_effects.py -k 'Wipe'
```

Replace `Wipe` with relevant effect names; record the terminals and platforms inspected.
Inspect skips: the canvas-anchoring manual test is currently marked skipped, so exercise
those scenarios directly with the CLI rather than counting them as verified.

For performance changes, attach before/after measurements with fixed seeds and frame/output
invariants, or explain intentional visual changes. Use the documented
[performance workflow](docs/performance.md). For unaffected areas, record a reasoned N/A
rather than claiming a test was performed. Human inspection cannot be replaced by green CI.

## 5. Review, merge, and verify the final commit

When QA passes on the latest revision, mark the PR ready. Wait for automated review to finish,
address findings, resolve conversations, and rerun affected checks. The maintainer reviews the
release evidence and separately authorizes squash merging.

After merging, identify the resulting release commit and wait for its `main` CI run to pass.
Changes to code, dependencies, packaging, or notes require renewed relevant QA. Preserve evidence
from the reviewed branch and confirm the merged tree contains the reviewed changes.
Freeze the chosen release commit; later commits on `main` are not automatically part of this release.

## 6. Build and approve the exact upload files

Check out the chosen merged commit in a clean, separate checkout and sync its locked development
tools. Build and validate into a new empty directory outside the checkout:

```sh
./.venv/bin/python tools/check_artifacts.py --output-dir /absolute/path/to/release-artifacts
```

This checks the direct wheel, source archive, and wheel rebuilt from that archive, including
clean installs outside the checkout and prototype exclusion. Retained output contains a direct
wheel and source archive at its root, plus a verification-only wheel in `from-sdist/`.

Record the full commit SHA, version, filenames, validation result, and SHA-256 checksums in the
release issue. Review metadata, README rendering, CLI help/version, and packaged files.
Select only the direct wheel and source archive for publication; do not upload the rebuilt duplicate.
Generate a checksum file for the two selected upload files, for example on macOS/Linux:

```sh
shasum -a 256 /absolute/path/to/release-artifacts/terminaltexteffects-0.16.0-py3-none-any.whl \
  /absolute/path/to/release-artifacts/terminaltexteffects-0.16.0.tar.gz \
  > /absolute/path/to/release-artifacts/SHA256SUMS
```

Keep those exact tested files unchanged through approval and upload. Rebuilding requires renewed
artifact validation and new recorded checksums.

Obtain explicit publication approval naming the version, commit, tag, and selected artifacts.
Use the existing `release-<version>` tag convention, for example `release-0.16.0`.
Verify the tag and PyPI version do not already exist before approving a new release.

## 7. Publish after approval

Use the approved commit and artifacts, not the current moving branch tip. Tag the exact commit:

```sh
release_commit=REPLACE_WITH_APPROVED_FULL_SHA
git tag -a release-0.16.0 "$release_commit" -m 'Release 0.16.0'
git push origin refs/tags/release-0.16.0
```

Confirm the remote tag resolves to the approved commit. Tag pushes currently do not run CI;
the recorded final-commit validation is required before pushing the tag.

Authenticate Twine using the maintainer's existing PyPI credential mechanism. Keep credentials
out of commits, command arguments, and release logs. Upload the two selected files explicitly:

```sh
./.venv/bin/twine upload --repository-url https://upload.pypi.org/legacy/ \
  /absolute/path/to/release-artifacts/terminaltexteffects-0.16.0-py3-none-any.whl \
  /absolute/path/to/release-artifacts/terminaltexteffects-0.16.0.tar.gz
```

Use the actual validated filenames. Twine uploads prebuilt files; do not rebuild during upload.
See [PyPA's packaging flow](https://packaging.python.org/en/latest/flow/).
Create a GitHub release from the existing tag using the same dated changelog section, attach
selected artifacts and checksums, review its draft, then publish under the recorded approval.
Do not auto-generate a second, divergent release-note history.

## 8. Verify publication and close the issue

Install the exact version from PyPI into a fresh environment outside the repository, without
editable installs or development-effect settings. Verify package and effect imports,
`tte --version`, both CLI entry points, and a short effect invocation. Test the minimum supported
Python version and confirm package metadata and published file checksums match the approved files.

Check the PyPI description/license, GitHub tag and notes, and public documentation links/version.
The site follows development `main` after successful push CI; it is not a versioned release site.
Verify the deployed commit banner, release notes, and relevant API pages using the
[deployment guide](.github/DOCUMENTATION.md). A strict local build does not publish the site.
Record the deployed commit or link an explicit follow-up before sign-off.
Attach publication URLs and verification evidence, then complete the release issue checklist and close the tracking issue.

## Failed or incomplete publication

If upload succeeds for only one file, inspect PyPI and compare the existing file with the
approved checksum before uploading only the missing artifact. Do not use `--skip-existing`
to conceal uncertainty or upload a rebuilt replacement under the same version.
If a published release is broken, stop promotion, document the impact, and prepare a new patch
release; evaluate PyPI yanking separately with maintainer approval. Preserve published tags and
artifacts rather than moving a tag or silently rewriting release history.
