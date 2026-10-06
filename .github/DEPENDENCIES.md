# Dependency updates

[dependabot.yml](dependabot.yml) maintains the root `pyproject.toml`/`uv.lock` project
and GitHub Actions references. Both ecosystems are checked weekly on Monday at 09:00
America/New_York. Routine minor and patch updates are grouped per ecosystem; routine major upgrades
remain individual PRs. Each ecosystem may have at most two open version-update PRs.
Security updates do not count toward this limit.

PRs are assigned to `ChrisBuilds` with `maintenance` and `ci` labels. Select milestones
during triage instead of permanently binding updates to one release. Keep action
references pinned to full commit SHAs with version comments; review the new revisions
and release notes. The existing read-only `Graph Update: uv` action supplies dependency
information; it does not replace these update PRs.

Configuration activates on the default branch after merge. GitHub may perform an
initial check before the first scheduled Monday. Inspect Dependabot update logs in the
repository dependency graph if expected PRs do not appear. No private runner, external
bot installation, or new credentials are needed.

## Triage a bot PR

Dependabot creates its branch and PR before a project issue exists. This is the narrow
exception to issue-first creation and branch naming. Keep its generated branch, then
apply the normal acceptance, metadata, changelog, and CI requirements before merge:

1. Review packages/actions, release notes, scope, and Python 3.9 compatibility. Create
   one tracking issue for the coherent batch with `ChrisBuilds`, `maintenance` + `ci`,
   and the intended milestone at creation. Unscheduled work uses `Release target: not
   scheduled` and no milestone. Add `Closes #<issue>` to the PR and mirror the milestone.
   Leave Project unset. Request `ChrisBuilds` as reviewer on bot-authored PRs.
2. Put the PR in draft while adding project-specific changes. Check out the bot branch
   and add `<issue>.skip.md` for internal tooling-only updates, or a user-facing fragment
   when dependency behavior affects users. Run
   `./.venv/bin/python tools/generate_changelog.py` and commit any refreshed preview.
   Do not use the PR number as an invented issue number or reuse this setup issue.
3. Sync the updated lockfile with `uv sync --locked --group dev`. Resolve tooling/config
   changes and run focused local tests as needed. Do not silently drop Python 3.9 support
   or replace SHA-pinned actions with floating tags to get an update through.
4. Push the fragment and related fixes to the same PR. Required CI checks must pass on
   the latest revision. Review subsequent bot rebases/commits again; recheck fragments,
   preview, and metadata if Dependabot rebuilds its branch.
5. Mark ready after verification. The maintainer reviews, explicitly authorizes the
   squash merge, and deletes the merged branch. There is no automatic merging.

Initial bot PRs normally fail the changelog-decision check until step 2 is complete.
This prevents merging an untriaged update. No bot-author bypass or privileged workflow
adds fragments or changes the bot's code automatically. Dependency and workflow changes
retain the full matrix, artifact checks, and applicable documentation checks. If a group
fails, diagnose or split it into coherent issues/PRs rather than disabling required checks.
Major upgrades get individual migration review even for development tools.

## Security updates and activation

Security fixes have a separate Python group so an urgent fix does not wait for the
weekly version-update batch. Grouping does not enable security updates by itself.
Automatic security updates, dependency graph, and alerts are enabled in GitHub settings.
Verify these under Settings -> Advanced Security / Code security when maintaining the setup.
The security group may include a necessary major upgrade; review its migration before merging.
Security updates still require triage and explicit merge authorization. This setup does
not resolve existing vulnerability alerts or enable automatic merging.

GitHub's [supported ecosystems](https://docs.github.com/en/code-security/reference/supply-chain-security/supported-ecosystems-and-repositories)
and [configuration reference](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference)
describe uv support, grouping, schedules, and limits. Verify the actual update logs and
first PR after activation; local YAML validation cannot exercise GitHub's updater.

## Dependency vulnerability gate

On every `pull_request` CI run (including drafts), Code quality runs the SHA-pinned official
[dependency-review action](https://github.com/actions/dependency-review-action). It blocks
newly introduced **high or critical** vulnerabilities in runtime, development, and unknown
scopes. License enforcement is disabled; this is a vulnerability gate, not a license policy.
The action uses existing `contents: read`, writes its job summary, and does not post PR
comments or need additional secrets/write permissions. It retries pending dependency
snapshots for up to 120 seconds.

The companion `tools/check_dependency_review.py` compares the action's reported uv changes
with both committed universal lockfiles. Every added/removed registry package/version pair
must appear, including transitive, development/build, and conditional Python/platform
alternatives. It normalizes Python package names and fails missing/empty/malformed output
for actual dependency changes. This guards against incomplete snapshots being mistaken for
clean reviews. The local project entry is excluded; non-registry dependencies in the head
lock fail pending explicit support/review. Removed unsupported dependencies do not prevent
remediation. The helper does not install packages or make network requests.

GitHub's graph was checked against the complete current lock and a historical dependency
update before introducing the gate. That does not guarantee future parser coverage; retain
the pair-diff guard and inspect graph warnings and results when dependencies change. The
review action also covers supported GitHub Actions changes; the pair guard checks uv only.
Source-only PRs with unchanged registry pairs legitimately have an empty uv comparison.

This is a differential check, not a full vulnerability audit. Unchanged vulnerable versions
and newly published advisories against existing dependencies can remain open; Dependabot
alerts/security updates remain the ongoing remediation channel. Registry markers are
reviewed conservatively: an affected conditional dependency is not exempt merely because
it is unused on the current CI interpreter. Unknown/unpublished vulnerabilities and unsafe
behavior without an advisory are outside this gate. Review release notes and integration.

Main pushes and manual CI runs do not run the PR differential action; they still run its
offline guard fixtures and normal QA. They do not substitute for ongoing Dependabot alerts.
No required check name is added: a gate failure fails the existing Code quality check.

### Diagnose a gate failure

- For a high/critical advisory, update/remove the affected version and review compatibility;
  preserve the supported Python minimum. Do not blanket-ignore older conditional versions.
- For missing pairs or snapshot warnings, wait for GitHub's graph update and retry the
  current revision. Inspect base/head refs and graph parsing before changing the guard.
  An API/graph outage is not a clean security result.
- Reproduce guard logic offline with captured dependency-review JSON in `DEPENDENCY_CHANGES`
  and `./.venv/bin/python tools/check_dependency_review.py --base <base-sha> --head <head-sha>`.
  Run `./.venv/bin/pytest -q tests/test_dependency_review.py` for fixtures. The official
  action requires GitHub's API; these fixtures do not claim to exercise hosted permissions.

### Exceptions

There are **no approved advisory exceptions** and no installed advisory allowlist. Existing
alerts are not automatically exemptions for newly introduced versions. Do not use warn-only,
`continue-on-error`, runtime-only scope, or blanket package exclusions to get a PR through.

Any future exception needs explicit maintainer approval in its own reviewed PR: exact
advisory/package/version scope, a linked tracking issue, exposure assessment and justification,
remediation plan, and expiry/review date. The PR must implement expiry validation before
introducing a timed allowlist so an expired exemption fails CI. Consider that the official
`allow-ghsas` input applies globally by advisory ID; do not pretend it is version-scoped.
Until that support is reviewed, fix the dependency instead of adding a bypass.
