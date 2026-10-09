# Security monitoring and ownership

Security monitoring is ongoing maintenance, separate from a passing PR. Dependabot
finds known dependency advisories; CodeQL analyzes source/workflows; dependency review
blocks certain newly introduced advisories. None guarantees a secure release or resolves
existing alerts. This procedure adds no scheduler, duplicate scanner, notification bot,
required merge gate or automatic alert dismissal.

## Ownership and triggers

`ChrisBuilds` is accountable for security triage, notification delivery and decisions.
An assigned agent performs the checks, records evidence, and reports unexpected findings
or broken monitoring to the primary agent/maintainer. A monitoring handoff names its next
owner using [AGENT_HANDOFF.md](AGENT_HANDOFF.md); ending an agent session does not create
a background monitor or guarantee future execution.

Review security health:

- Weekly, after the Monday Dependabot update window and Wednesday CodeQL scan.
- Before release sign-off, even if routine PR CI is green.
- After a notification, unexpected updater failure, security configuration/action change,
  or change to dependency/tooling support, runner isolation or exposure.

The maintainer owns scheduling this weekly review. Existing scans/updates run automatically,
but this triage procedure is human/agent initiated; there is no automatic freshness alert.
GitHub notifications supplement this review, not replace it. No response-time guarantee
is made to reporters; private reporting follows [SECURITY.md](../SECURITY.md).

## Check CodeQL freshness and health

The current schedule is Wednesday 06:17 UTC. Inspect both Python and Actions jobs and
uploaded analyses on `refs/heads/main`, not merely the workflow's overall green badge:

```sh
gh run list --all --workflow codeql.yml --branch main --limit 20 \
  --json databaseId,attempt,event,headSha,createdAt,status,conclusion,url
gh api --paginate 'repos/ChrisBuilds/terminaltexteffects/code-scanning/analyses?ref=refs%2Fheads%2Fmain&per_page=100' \
  --jq '.[] | {created_at,commit_sha,category,error,warning,tool: .tool.name}'
gh api --paginate 'repos/ChrisBuilds/terminaltexteffects/code-scanning/alerts?state=open&ref=refs%2Fheads%2Fmain&per_page=100' \
  --jq '.[] | {number,state,rule: .rule.id,tool: .tool.name,html_url}'
```

Run from the repository, or add `--repo ChrisBuilds/terminaltexteffects` to `gh run`
commands. These APIs require access to security results. An authorization error, disabled
feature, rate limit, empty analysis history or failed request is **unverified**, not clean.
A successful empty *alert* list is different from missing/failed *analysis* evidence.
Paginate so older pages do not conceal open findings or category results.

For each CodeQL category `/language:python` and `/language:actions`, record the newest
successful extraction/analysis/upload date and SHA. Inspect errors, warnings and source
coverage through the run logs and Security → Code scanning tool status; an analysis row
alone is insufficient if upload/source extraction is incomplete. Successful analysis can
still have open findings. The two categories must both be accounted for; one succeeding
cannot hide the other failing.

Use these operational thresholds, measured in UTC from the last verified successful
upload for **each category**:

- Up to 9 days: within the weekly schedule plus a two-day delay allowance. Any newer
  failed run still needs investigation; recent success does not erase a failed attempt.
- More than 9 days, or a category never successfully uploaded: overdue. Check schedule
  enablement, queued/failed/cancelled runs and GitHub service status; report the gap and
  diagnose before a manual main dispatch.
- More than 14 days: escalate the unresolved monitoring gap to the maintainer and track
  a scoped follow-up. Do not describe scans as current or security validation complete.

Before release sign-off, both categories must have valid successful results within the
9-day window, new/open findings must be triaged, and later failures must be explained.
These are process criteria, not a new required GitHub check. Weekly scans naturally lag
main: record scanned and current SHAs explicitly. If security-relevant code/workflows
changed after the latest scan, dispatch main and verify both uploads rather than claiming
that older analysis covers those changes. Analysis on main does not scan an unmerged
release branch; record that gap and verify the merged release code before publication.

```sh
gh workflow run codeql.yml --ref main
```

Identify the new run by event/time, monitor both jobs, and recheck uploaded analyses and
alerts. Dispatch success is not scan success. Preserve failed-run evidence; do not retry
indefinitely or enable a second default setup. See [CODEQL.md](CODEQL.md) for scope and triage.

## Check dependency alerts, graph and updater health

Routine updates check Monday at 09:00 America/New_York; security updates are separate
and can arrive at other times. Inspect all open alerts and bot PRs, including advisories
below the PR gate's high/critical threshold:

```sh
gh api --paginate 'repos/ChrisBuilds/terminaltexteffects/dependabot/alerts?state=open&per_page=100' \
  --jq '.[] | {number,state,severity: .security_advisory.severity,ghsa: .security_advisory.ghsa_id,package: .dependency.package.name,html_url}'
gh pr list --author 'app/dependabot' --state open --limit 100 \
  --json number,title,url,headRefName,isDraft
```

The PR command is a convenience view (increase its limit for a larger backlog); the
paginated alert API and Security dashboard remain the authoritative advisory inventory.
Missing bot PRs do not establish that dependencies are patched. Inspect Dependabot
updater logs in the dependency graph for **both uv and GitHub Actions** ecosystems,
workflow/settings enablement, graph/SBOM coverage and resolution errors. `Graph Update: uv`
runs are dynamically supplied by GitHub; their names/IDs are not stable workflow files.
After dependency changes, verify the submitted graph includes the current lock's affected
versions/conditional environments. A successful graph submission is not a security audit.

Each weekly review should find the latest updater attempt for both ecosystems. More than
9 days without an attempt is overdue and needs investigation; an attempt that failed needs
triage even when it is recent. Record API/UI evidence and timestamps; if updater logs or
graph data are inaccessible, state the limitation rather than fabricating freshness.

### Known native-Python-3.9 pytest alert

Track GHSA-6w46-j5rx-g56g in [#154](https://github.com/ChrisBuilds/terminaltexteffects/issues/154).
The native 3.9 pytest dependency remains affected; the patched upstream line requires
Python 3.10+. A security-update resolution failure for this constraint is known, not proof
that the whole updater is healthy or that other failures may be ignored.

At each review, check for a compatible upstream fix, changes to the advisory, and changes
to support/runner exposure. Keep the alert and issue open until remediation is verified.
Follow [DEPENDENCIES.md](DEPENDENCIES.md#runtime-and-tooling-python-support) for the approved
no-wrapper disposition and reassessment on shared Unix/persistent runners. Do not dismiss,
allowlist, fork, add a workaround or raise runtime support solely to clear the dashboard.
New findings require their own exposure assessment; they do not inherit this disposition.

## Notifications and escalation

The maintainer verifies their GitHub account/repository security and Actions notification
preferences and the intended delivery channel. Confirm delivery with a real benign update
or failure already in history, without creating a vulnerability or breaking CI for a test.
Account preferences, subscriptions and workflow participation can affect delivery; documents
cannot configure personal notifications or promise every scheduled failure sends email.
Record delivery as verified or unverified. No additional email/Slack messages or external
services are configured by this procedure.

For a new alert, inspect severity, affected versions/source trace, realistic input exposure,
and whether released users or only tooling are affected. High/critical or plausible runtime
exposure warrants prompt maintainer attention; lower-severity tooling findings still require
recorded triage. Preserve original evidence and use a scoped issue/branch/PR for a fix.
Sensitive reports/traces belong in the private security route; public tracking is sanitized.
Alerts must not be dismissed, accepted as risk or excluded without explicit maintainer
approval. A fix is complete only after appropriate tests and post-merge scan/graph evidence
confirm remediation; changing a lock does not publish a fixed package.

## Review record

Update an existing tracking issue or handoff comment when appropriate; use a scoped
maintenance issue for an unexplained failure/gap. Keep internal routine records in the
local development QA log. Avoid a public comment for every poll or repeated known alert.

```markdown
## Security health review
- Reviewed at (UTC), owner and trigger:
- Current main SHA:
- Python / Actions: run and attempt, analyzed SHA, upload date, scope/warnings, freshness:
- Open CodeQL findings: IDs and disposition (or verified none):
- Dependabot alerts: IDs/GHSA, exposure, tracking issue and disposition:
- uv / Actions updater: latest attempt date, result and unresolved errors:
- Dependency graph/lock verification and access limits:
- Notification delivery: verified/unverified, owner (no private account details):
- Unexpected issues reported, follow-up owner/action and next review date:
```

Record what was actually checked and any inaccessible evidence. Known tracked risk,
failed/stale scans and unresolved notification delivery are explicit limitations, not a
blanket clean-security conclusion.
