# Exhaustive release validation

This manual workflow runs the automated suite with `--exhaustive-effect-args` instead
of the routine deterministic pairwise parameter selection. It uses Linux/Python 3.14;
the normal required CI matrix still validates every supported Python version and the
focused macOS/Windows cases. Manual/visual tests remain excluded by pytest configuration
and require separate human inspection. The exhaustive suite can be substantially larger
and more expensive than normal CI; it never runs on ordinary pushes or PRs.

## Dispatch from the release checklist

Release preparation authorizes agents/developers to dispatch validation, monitor it,
investigate failures and record evidence. It does not authorize merge or publication.
The workflow must first exist on `main`. Resolve the candidate from the release PR's
current head, not GitHub's synthetic PR merge revision:

```sh
gh pr view RELEASE_PR_NUMBER --json headRefOid --jq .headRefOid
```

Copy that full lowercase 40-character SHA into the following command:

```sh
gh workflow run exhaustive.yml --ref main -f commit=FULL_CANDIDATE_SHA
gh run list --workflow exhaustive.yml --event workflow_dispatch --limit 10 \
  --json databaseId,displayTitle,createdAt,status,conclusion,url
```

Identify the newly created run by its `Exhaustive / FULL_CANDIDATE_SHA` title and
creation time; if multiple dispatches match, verify the intended run rather than
assuming the first result. Then use its actual numeric ID:

```sh
gh run watch RUN_ID --exit-status
gh run view RUN_ID --json url,status,conclusion,jobs
gh run download RUN_ID --name exhaustive-python-3.14-FULL_CANDIDATE_SHA \
  --dir /path/to/release-evidence
```

The same operation is available through Actions → Exhaustive release validation →
Run workflow. Select `main` for the workflow definition and enter the candidate SHA.
Moving branch names, tags and abbreviated SHAs are rejected. Checkout is restricted
to this repository and its resolved HEAD is verified against the supplied SHA.
The workflow definition comes from `main`; candidate code, tests, configuration and
locked dependencies come from the exact requested commit. Advancing the release branch
during the run cannot change what it tests. Candidates must contain the current test
infrastructure, including `tools/write_test_context.py` and the exhaustive pytest option.

## Evidence and interpretation

Record the run URL/ID, candidate full SHA, workflow-definition SHA, Python version,
final job conclusion, pytest exit status, actual collected results/skips, and evidence
location in the release issue/PR. Download artifacts before their **30-day retention**
expires; they are temporary CI evidence, not permanently stored release artifacts.

The artifact contains:

- `revision.txt`: verified candidate and workflow-definition commits.
- `context.json`: exact candidate reproduction metadata and interpreter/test-tool versions.
- `pytest.log`: combined output and slowest test durations.
- `exhaustive.xml`: JUnit results, when pytest completes report generation.
- `pytest-exit-status.txt`: pytest's exit status, when the test command finishes.

The context's `revision` and `pr_head` identify the candidate; GitHub's dispatch run
`headSha` identifies the workflow definition on main. Use `revision.txt` to distinguish
them. Shell output is logged normally; metadata never dumps the environment.
Uploads are attempted after success or failure once revision evidence exists, except
cancellation. Early checkout failures, hard cancellation, the six-hour job limit or
other termination may leave incomplete/missing evidence. Missing files are not passes.
The 120-second stalled-test timer prints tracebacks without stopping or retrying tests.

Sign off only when the correct run/job succeeds, pytest reports zero exit status,
revision/context agree with the candidate, JUnit/logs confirm completed exhaustive
collection/execution, and skips are inspected. An upload failure makes the job fail.
There are no automatic retries, allow-failure flags or publishing credentials.
Investigate failures using [test diagnostics](TEST_DIAGNOSTICS.md); an agent should
report unexpected failures to the primary agent/maintainer and preserve the original
run link even if a later rerun passes. If the six-hour limit is insufficient, investigate
and propose a partitioned suite rather than treating partial work as complete.

Any release-candidate change requires fresh exhaustive evidence for the new candidate.
After squash merge, record both reviewed and merged SHAs and verify their trees match;
if they differ, rerun against the merged release commit before approval. Main CI must
also pass. A passing exhaustive run does not replace human QA, packaging validation,
security checks, review, or explicit publication approval.

## Workflow changes

Run `tools/check_workflows.py` with actionlint/ShellCheck and build docs strictly.
To check hosted plumbing after workflow changes without running the expensive suite,
dispatch an intentionally invalid `commit` (such as `invalid`) from main: it must fail
input validation before checkout/install/tests. Record this expected failed probe
explicitly; it provides no exhaustive release coverage. Actual successful hosted
execution and artifact contents must be verified at the next release-candidate run.
