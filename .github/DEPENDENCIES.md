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
At setup, the repository reported automatic security updates disabled. After this
configuration is merged, enable **Dependabot security updates** under repository
Settings -> Advanced Security / Code security, with dependency graph and alerts enabled.
The security group may include a necessary major upgrade; review its migration before merging.
Security updates still require triage and explicit merge authorization. This setup does
not resolve existing vulnerability alerts or enable automatic merging.

GitHub's [supported ecosystems](https://docs.github.com/en/code-security/reference/supply-chain-security/supported-ecosystems-and-repositories)
and [configuration reference](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference)
describe uv support, grouping, schedules, and limits. Verify the actual update logs and
first PR after activation; local YAML validation cannot exercise GitHub's updater.
