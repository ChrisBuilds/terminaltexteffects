# Post-merge verification and recovery

A green PR validates its proposed integration. After an authorized squash merge, verify
main CI and live documentation separately. This procedure adds no workflow, required
check or publishing action. The merge handler owns verification until it is completed
or explicitly handed off using [AGENT_HANDOFF.md](AGENT_HANDOFF.md). Report unexpected
failures to the primary agent/maintainer promptly; do not wait silently or declare the
work complete while verification is pending. Avoid publishing a comment for every poll.

## 1. Record the merge and find exact push CI

From a repository checkout (or by adding `--repo ChrisBuilds/terminaltexteffects`
to the `gh pr`/`gh run`/`gh workflow` commands), replace
uppercase placeholders with actual values:

```sh
gh pr view PR_NUMBER --json url,state,mergedAt,mergeCommit
gh run list --workflow ci.yml --branch main --event push --commit MERGED_FULL_SHA \
  --limit 20 --json databaseId,attempt,headSha,event,status,conclusion,url
```

Use the PR's squash `mergeCommit.oid`, not its old branch head or synthetic PR merge
SHA. Identify the matching push run and attempt, then inspect and monitor it:

```sh
gh run view CI_RUN_ID --json headSha,event,attempt,status,conclusion,jobs,url
gh run watch CI_RUN_ID --exit-status
```

Verify the SHA/event, all required job results, and actual executed scope against
[CI.md](CI.md). Documentation-only runs intentionally skip broad tests with successful
placeholder steps; record that fact rather than claiming the suite ran. Code-bearing
changes must actually execute the appropriate matrix. Dependency review is a PR gate;
its absence in push CI is expected. Main CI does not replace PR review or release QA.

A queued run is pending, not failed. Check GitHub runner/service status for sustained
queues before dispatching duplicates. If a run is absent, expand the search window and
inspect Actions/trigger configuration and permissions; absence is not success. Record
which attempt you inspected, especially after reruns.

## 2. Handle main advancing

```sh
gh api repos/ChrisBuilds/terminaltexteffects/git/ref/heads/main --jq .object.sha
```

Main CI cancels superseded runs. If the merged commit's run was cancelled because main
advanced, record it as cancelled/unverified. Confirm the merge is contained in the newer
main history, follow the newer main push run, and record its tested SHA and result as
replacement integration evidence. Do not claim the original exact commit passed. Release
validation still needs its selected exact release commit and follows [RELEASING.md](../RELEASING.md).
Do not dispatch old CI merely to obtain a green badge unless exact-revision diagnosis or
release validation requires it. An unrelated cancellation is not proof of supersession.

## 3. Verify deployment and the public site

Successful current-main **push CI** starts `docs.yml`. List recent deployments:

```sh
gh run list --workflow docs.yml --limit 20 \
  --json databaseId,attempt,event,headSha,status,conclusion,createdAt,url
gh run view DOCS_RUN_ID --json status,conclusion,jobs,url
```

Read its build/selection/deploy logs and summary to identify the source CI and selected
documentation SHA. The deployment run's `headSha` alone is not proof of what was built;
selection uses the triggering successful CI SHA or current-main successful push CI for
manual dispatch. A green run that reports skipped publication is not a deployment.
Confirm the **Deploy GitHub Pages** step actually succeeded, not just the build job.
Waiting for `github-pages` environment approval is pending; do not change its rules to
bypass a required maintainer approval.

Open the [public site](https://chrisbuilds.github.io/terminaltexteffects/) and inspect:

- The development banner's commit link: its full `/tree/<SHA>` target must match the
  actual deployed SHA (the visible banner abbreviates it to seven characters).
- The introduction, navigation, a deep API page, and relevant changed documentation.
- Images and changelog when affected. Record inspected pages and any uninspected scope.

A local strict build does not establish live publication. If the banner is stale after
a successful deployment, retry the page without browser cache and allow brief propagation;
then inspect deployment evidence instead of repeatedly dispatching. The site describes
main development, not necessarily the published PyPI version.

If main advances while building or awaiting approval, the workflow intentionally skips
stale publication. Follow the newer main CI and deployment, record the superseded run,
and verify its newer live banner. Main can also advance during an active upload: an older
site may briefly be live before the newer successful CI deploys. Verify the newest tested
deployment; do not label an intentional skip or temporary lag as successful publication.

## 4. Investigate and recover

Preserve the original run URL, attempt, tested SHA, first failing step and relevant
artifacts before retrying. Follow [TEST_DIAGNOSTICS.md](TEST_DIAGNOSTICS.md) for JUnit,
context, stalled-test traces and focused reproduction. Missing artifacts and partial runs
are incomplete evidence. Check current main before choosing recovery.

| Finding | Response |
| --- | --- |
| Evidence of a transient runner, download or service outage | Explain the evidence and retry the failed jobs on the same run once; retain the original failure and inspect the new attempt. A repeated failure requires investigation/reporting, not a retry loop. |
| Assertion, type, formatting, stale generated file, packaging or docs-source defect | Reproduce narrowly; create/link a scoped follow-up issue and normal branch/draft PR. Do not edit main. Use the existing issue workflow and authorization limits; report scope changes for a maintainer decision. |
| Main push CI failed or is pending | Fix/investigate CI first. Documentation manual dispatch cannot bypass matching successful current-main push CI. |
| Pages deployment failed after successful current-main CI | Inspect logs, Pages source and environment configuration. Retry an evidenced transient failure; fix source/configuration through a PR. Settings/approval changes require a maintainer decision. |
| Intentional stale-build skip | Follow the newer tested main deployment; do not rerun the stale build as a rollback. |
| Unexpected security, behavioral or scope issue | Report promptly to the primary agent/maintainer; use the private security route for sensitive findings. Do not dismiss alerts, weaken checks or expand authorization. |

For an evidence-backed transient CI failure:

```sh
gh run view CI_RUN_ID --log-failed
gh run rerun CI_RUN_ID --failed
```

For a documentation retry after successful push CI matching current main:

```sh
gh workflow run docs.yml --ref main
```

Identify and inspect the new run; dispatch returning successfully is not deployment
success. If several runs match, use event/time and logs to disambiguate. Failed deployment
leaves the last successful site available. Reverting source uses a reviewed PR and normal
CI/deployment. Reverts, environment changes, switching to legacy `gh-pages`, tagging and
publication require their appropriate explicit maintainer authorization. Never force-push
main, move release tags or disable checks to recover. See [DOCUMENTATION.md](DOCUMENTATION.md).

## 5. Record completion or a concrete handoff

Update the existing PR checkpoint with the outcome (or add one concise post-merge comment
if none exists); link a follow-up issue for unresolved problems. Internal local logs can
supplement the public evidence. A closed linked issue does not erase outstanding verification.

```markdown
## Post-merge verification
- PR / squash merge SHA:
- Main CI run / attempt / tested SHA / conclusion / actual scope and skips:
- Superseded or failed runs and explanation (or none):
- Docs run / attempt / actual deployed SHA / deploy-step result:
- Live banner full SHA / inspected pages / verification time (UTC):
- Recovery actions, original failure evidence and follow-up issue (or none):
- Outcome: complete, or pending/failed with next owner and concrete action.
```

Do not mark complete until main integration and live publication are verified, or an
explicit handoff records the unresolved outcome and owner. A handoff transfers the work;
it does not turn pending/failed checks into passes. Keep credentials, private paths and
sensitive exploit details out of public records.
