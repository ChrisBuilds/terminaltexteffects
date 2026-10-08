# CodeQL security scanning

[codeql.yml](workflows/codeql.yml) scans Python source and GitHub Actions workflows with
GitHub's official CodeQL action. It supplements behavioral tests, Ruff/Pyright and the
advisory-based dependency gate with analysis of potentially unsafe code/data flows.

## Triggers and implementation

- Weekly on **Wednesday at 06:17 UTC** (`17 6 * * 3`); scheduled execution follows main.
- Manual **Actions -> CodeQL security scanning -> Run workflow**, selecting **main**.
- No PR, push, `pull_request_target`, or `workflow_run` trigger. This rollout adds no
  required PR checks and does not change branch protection.

The job rejects non-main manual selections and checks out the event's exact main SHA
without persisting Git credentials. Two independent Ubuntu 24.04 matrix jobs analyze
`python` and `actions`, with 30-minute limits and separate `/language:<language>` categories.
Concurrency replaces obsolete scans of the same ref. Failure in one language does not
cancel the other. There is no extra pytest run, Python-version matrix, package installation,
build, release, or deployment step.

The official init/analyze actions are pinned to the reviewed release commit, with version
comments. Interpreted languages use `build-mode: none`. Initially the built-in **default
security queries** run, without blanket path/query exclusions. Python analysis can include
maintenance tools and tests as well as the shipped package; findings need context review.
This is not an exhaustive security audit or a proof that external plugins are safe.

Top-level permissions are `contents: read`; only the analysis job receives
`security-events: write` to upload results. It has no contents-write, PR-write, publishing,
Pages or OIDC permission and uses the built-in token without extra credentials. Upload or
analysis errors fail the scan visibly; they are not suppressed with `continue-on-error`.
A successful job means the analysis/upload succeeded, not that all alerts are resolved.

## Activation and first scan

The workflow must reach main before its schedule/manual entry is available. GitHub default
setup was not configured when this workflow was introduced; use this repository-owned
advanced setup rather than enabling a second default scan alongside it.

After the maintainer merges the PR:

1. Manually dispatch the workflow on main. Both language jobs must complete and upload
   successfully. Check the selected commit, categories and analyzed-source coverage in
   **Security -> Code scanning** / the tool status page.
2. Inspect extraction/analysis logs for skipped files and unsupported syntax. Resolve
   failures or unexpected omissions rather than treating an empty alert list as evidence
   that all intended source was analyzed.
3. Record the commit, run URL, per-job duration, query/tool versions, analyzed scope and
   initial alert triage in the local development QA log. Local actionlint validation cannot
   establish hosted extraction, upload permissions or the initial findings.
4. Review alert noise and measured runtime before adding query suites, PR/push triggers,
   required checks or code-scanning merge rules. Those are separate reviewed changes.

Scheduled runs can be delayed or disabled by GitHub. If the latest successful scan is old,
check workflow enablement and failed/queued jobs, then dispatch main after diagnosing the
cause. See GitHub's [scheduled event documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

## Triage findings

Inspect alerts in [Code scanning](https://github.com/ChrisBuilds/terminaltexteffects/security/code-scanning):
rule, severity, source/sink trace, affected code, input trust and realistic exposure.

- For an actionable finding, create a scoped tracking issue with the normal assignee,
  type/area labels and release target. Follow issue -> branch -> draft PR, verify the
  unsafe path, add meaningful regression coverage and the appropriate changelog fragment.
  Confirm the reviewed fix in a subsequent main scan after its authorized merge.
- If exploit details are sensitive, use the private reporting/advisory route in
  [SECURITY.md](../SECURITY.md) and coordinate disclosure instead of publishing a public
  proof of concept or confidential trace. Sanitized process notes can remain public.
- For a false positive or deliberately accepted risk, require explicit maintainer review
  before dismissing the alert. Record the reason/evidence and any follow-up/review date in
  GitHub's dismissal explanation or linked tracking issue. Do not add blanket exclusions
  or weaken token permissions merely to produce a clean dashboard.

CodeQL does not create or merge fixes automatically. Normal CI and explicit maintainer
merge approval remain required; release publishing stays governed by RELEASING.md.

## Maintain and verify configuration

Existing weekly Dependabot GitHub Actions updates cover the new SHA-pinned references.
Review release notes and resulting scan behavior during update triage; pin updates do not
replace review. Keep both init/analyze references on the same reviewed release. Do not
switch to floating tags or enable broader query packs without deliberate review.

For workflow changes, use the project's pinned actionlint and required ShellCheck helper:

```sh
./.venv/bin/python tools/check_workflows.py
```

Stage new workflow files first because its default inventory is Git-tracked. Strict docs,
changelog validation and diff checks apply to associated guidance. Ordinary PR CI validates
this workflow as configuration; it does not execute a privileged scan of an issue branch.

GitHub documents [advanced setup](https://docs.github.com/en/code-security/how-tos/find-and-fix-code-vulnerabilities/configure-code-scanning/configuring-advanced-setup-for-code-scanning),
[workflow options and query suites](https://docs.github.com/en/code-security/reference/code-scanning/workflow-configuration-options),
and the [official action/build-mode permissions](https://github.com/github/codeql-action).

## Ongoing monitoring ownership

Follow [SECURITY_MONITORING.md](SECURITY_MONITORING.md) for weekly/pre-release review,
per-category freshness thresholds, dependency updater/graph health, notification ownership,
escalation and the evidence template. Failed or stale scans and inaccessible security
results are not clean findings. Maintainer-owned triage is separate from automatic scans.
