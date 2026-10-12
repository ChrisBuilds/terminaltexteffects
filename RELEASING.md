# Releasing

Track each release in an issue created from the
[release template](.github/ISSUE_TEMPLATE/release.md), and record evidence there as you go.
Preparing a release authorizes preparation and QA only. Merging the release PR needs the
maintainer's instruction. Tagging and uploading need explicit approval naming the version, commit,
and tag.

## 1. Prepare the release branch

Branch from current `main` as `release/<issue-number>-<version>`. Promote any finished effects in
their own PRs first. Then:

1. Set `[project].version` in `pyproject.toml`, then run `uv lock` and `uv sync --locked --group dev`.
2. Update [SUPPORT.md](SUPPORT.md) for the new release's Python and platform requirements.
3. Review pending fragments for accuracy, duplicates, and migration notes, then assemble the notes:

   ```sh
   ./.venv/bin/towncrier build --draft --version X.Y.Z --date YYYY-MM-DD
   ./.venv/bin/python tools/generate_changelog.py --clear
   ./.venv/bin/towncrier build --yes --version X.Y.Z --date YYYY-MM-DD
   ./.venv/bin/python tools/generate_changelog.py
   ```

4. Commit the version, lockfile, dated changelog section, and consumed fragments together. Release
   PRs don't add a fragment of their own. Check the result with
   `./.venv/bin/python tools/generate_changelog.py --check --base origin/main`.

## 2. Automated QA

Open a draft PR with `Refs #<release-issue>`. All required CI checks must pass on the latest commit,
including the full test matrix.

Run the exhaustive effect-argument suite against the PR's head commit. It uses the workflow from
`main` and the code from the given full SHA:

```sh
sha=$(gh pr view <release-pr> --json headRefOid --jq .headRefOid)
gh workflow run exhaustive.yml --ref main -f commit="$sha"
gh run list --workflow exhaustive.yml --limit 3
```

Record the run link and result in the release issue. Rerun it if the candidate changes. Check
**Security → Code scanning** and **Dependabot alerts** for untriaged findings, and run a CodeQL scan
(`gh workflow run codeql.yml --ref main`) if security-relevant code changed since the last scan.

## 3. Human QA

Automated tests can't judge how an animation looks. In a real terminal, inspect each changed effect
for:

- appearance, pacing, and the final text;
- small, multiline, sparse, and wide-character input;
- color modes (truecolor, `--xterm-colors`, `--no-color`) and existing-color handling;
- narrow and wide terminals, wrapping, interruption, and cursor restoration.

Focused visual tests help:

```sh
./.venv/bin/pytest -s -m visual tests/test_effects.py -k '<Effect>'
./.venv/bin/pytest -s -m manual tests/test_effects.py -k '<Effect>'
```

The canvas-anchoring manual test is skipped; exercise anchoring directly with the CLI. Record the
terminals and platforms you checked, and mark anything not applicable as N/A with a reason.

## 4. Merge

Mark the PR ready, address review findings, and get the maintainer's merge instruction. After the
squash merge, confirm that `main` CI passes for the merged commit and that the merged tree matches
what you reviewed (`git diff REVIEWED_SHA MERGED_SHA`). If they differ, rerun the exhaustive suite.
That merged commit is the release commit.

## 5. Build and approve artifacts

In a clean checkout of the release commit, after syncing tools:

```sh
./.venv/bin/python tools/check_artifacts.py --output-dir /absolute/path/to/release-artifacts
shasum -a 256 /absolute/path/to/release-artifacts/terminaltexteffects-X.Y.Z{-py3-none-any.whl,.tar.gz}
```

This validates the wheel, the sdist, and a wheel rebuilt from the sdist, including clean installs and
exclusion of development effects. Upload only the top-level wheel and sdist, not `from-sdist/`.
Record their checksums in the issue, then get publication approval naming the version, commit, tag
(`release-X.Y.Z`), and files.

## 6. Publish

```sh
git tag -a release-X.Y.Z <approved-sha> -m 'Release X.Y.Z'
git push origin refs/tags/release-X.Y.Z
./.venv/bin/twine upload /absolute/path/to/release-artifacts/terminaltexteffects-X.Y.Z{-py3-none-any.whl,.tar.gz}
```

Keep PyPI credentials out of commands and logs. Create the GitHub release from the tag, using the
dated changelog section as the notes.

## 7. Verify and close

Install `terminaltexteffects==X.Y.Z` from PyPI into a fresh environment on the minimum supported
Python. Check `tte --version`, both CLI names, a short effect run, and the library import. Confirm the
PyPI page and the GitHub release, then close the release issue.

If an upload partly fails, compare what's on PyPI with the recorded checksums and upload only the
missing file. Never re-upload a rebuilt file under the same version. If a release is broken, ship a
patch release; never move a published tag.
