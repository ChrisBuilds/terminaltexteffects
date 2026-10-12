# Releasing

Track each release in an issue created from the
[release template](.github/ISSUE_TEMPLATE/release.md), and record evidence there as you go.
Preparing a release authorizes preparation and QA only. Merging the release PR needs the
maintainer's instruction. Pushing the release tag needs explicit approval naming the version and
commit, and publishing waits for the maintainer's approval in the `pypi` environment.

## 1. Prepare the release branch

Branch from current `main` as `release/<issue-number>-<version>`. Promote any finished effects in
their own PRs first. Then:

1. Set `[project].version` in `pyproject.toml`, then run `uv lock` and `uv sync --locked --group dev`.
2. Update [SUPPORT.md](SUPPORT.md) for the new release's Python and platform requirements.
3. Review pending fragments for accuracy, duplicates, and migration notes, then assemble the notes:

   ```sh
   ./.venv/bin/towncrier build --draft --version X.Y.Z --date YYYY-MM-DD
   ./.venv/bin/towncrier build --yes --version X.Y.Z --date YYYY-MM-DD
   ```

4. Commit the version, lockfile, dated changelog section, and consumed fragments together. Release
   PRs don't add a fragment of their own; consuming fragments into a dated section satisfies
   CI's changelog check. Verify with `./.venv/bin/python tools/changelog.py --base origin/main`.

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

## 5. Tag and publish

Publishing is automated by [`release.yml`](.github/workflows/release.yml) using PyPI Trusted
Publishing; no API token is involved. Tagging needs the maintainer's publication approval naming the
version and commit.

```sh
git tag -a release-X.Y.Z <release-sha> -m 'Release X.Y.Z'
git push origin refs/tags/release-X.Y.Z
```

The workflow checks that the tag matches the `pyproject.toml` version and points to a commit on
`main`, then builds and validates the wheel and sdist with `tools/check_artifacts.py` (including
clean installs and exclusion of development effects). The run summary lists their SHA-256 checksums.

The **Publish to PyPI** job then waits for approval in the `pypi` environment. Review the build
job's result and checksums, record the checksums in the release issue, and approve. The job uploads
both files with provenance attestations, and a final job creates the GitHub release from the tag with
the dated changelog section as notes.

**Dry run:** run the workflow manually from `main` (`gh workflow run release.yml --ref main`). It
builds `X.Y.Z.devN` and, after approval in the `testpypi` environment, publishes it to TestPyPI. Do
this before the first automated release and after changing the workflow.

## 6. Verify and close

Install `terminaltexteffects==X.Y.Z` from PyPI into a fresh environment on the minimum supported
Python. Check `tte --version`, both CLI names, a short effect run, and the library import. Confirm the
PyPI page shows the attestations and the GitHub release exists, then close the release issue.

If the build job fails, nothing was published. Fix the problem through a PR, have the maintainer
delete the unpublished tag (the "Protect published release tags" ruleset blocks tag deletion, so it
must be disabled briefly), and tag the fixed commit. If publishing fails partway, rerun the failed jobs in the same run: reruns skip files already
on PyPI, and the job then verifies that PyPI holds exactly the run's files with matching SHA-256
digests, so a missing, extra, or different file fails before the GitHub release is created. Never publish a rebuilt file under an existing
version. If
a release is broken, ship a patch release; never move a published tag.

## One-time setup

- PyPI → terminaltexteffects → Publishing → add a GitHub trusted publisher: owner `ChrisBuilds`,
  repository `terminaltexteffects`, workflow `release.yml`, environment `pypi`. Add the same on
  TestPyPI with environment `testpypi`.
- GitHub → Settings → Environments: create `pypi` and `testpypi`, each with the maintainer as a
  required reviewer and deployments limited to `release-*` tags (`pypi`) or `main` (`testpypi`).
- After the first automated release, delete the old PyPI API token.
